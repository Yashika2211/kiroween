"""Autopsy orchestration: clone, examine, and write the Death Certificate."""

from __future__ import annotations

import asyncio
import time
from collections.abc import Awaitable, Callable
from pathlib import Path
from typing import Any

import httpx

from necromancer.autopsy.clone import clone_repo, first_commit_date, last_commit_date
from necromancer.autopsy.decay import DecayInputs, compute_decay
from necromancer.autopsy.deps import find_dependencies
from necromancer.autopsy.loc import count_python_lines, enforce_limits
from necromancer.autopsy.markers import MarkerScan, scan_repo
from necromancer.autopsy.osv import scan_vulnerabilities
from necromancer.autopsy.pypi import check_dependencies
from necromancer.autopsy.verdict import write_verdict
from necromancer.github.client import GitHubClient, GitHubError
from necromancer.github.urls import RepoRef
from necromancer.models import DeathCertificate, Dependency, RunResult, VitalRecords
from necromancer.sandbox.runner import SandboxRunner
from necromancer.workspace import Workspace, iter_python_files

Emit = Callable[[str, dict[str, Any]], Awaitable[None]]

# Steps shown in the UI, in order.
STEPS = [
    ("exhume", "Exhuming the body (git clone)"),
    ("measure", "Measuring the remains"),
    ("records", "Pulling vital records from GitHub"),
    ("examine", "Examining every file for Python 2 markers"),
    ("toxicology", "Toxicology: dependencies and known vulnerabilities"),
    ("probe", "Checking for a pulse (pip install on Python 3.12)"),
    ("verdict", "Writing the Death Certificate"),
]

MAX_MARKERS_IN_CERT = 300


async def _noop(_type: str, _data: dict[str, Any]) -> None:
    return None


def requirement_files(root: Path) -> list[str]:
    found: list[str] = []
    for pattern in ("requirements*.txt", "requirements/*.txt"):
        for path in sorted(root.glob(pattern)):
            name = path.name.lower()
            if path.is_file() and not path.is_symlink() and "doc" not in name:
                found.append(path.relative_to(root).as_posix())
    return found


def detect_tests(root: Path) -> bool:
    for path in iter_python_files(root):
        rel = path.relative_to(root)
        name = rel.name
        if name.startswith("test_") or name.endswith("_test.py"):
            return True
        if any(part in {"tests", "test"} for part in rel.parts[:-1]) and name != "__init__.py":
            return True
    return False


class AutopsyService:
    def __init__(
        self,
        *,
        sandbox: SandboxRunner,
        github_token: str | None = None,
        max_lines: int = 5000,
        max_repo_mb: int = 50,
        http: httpx.AsyncClient | None = None,
    ) -> None:
        self.sandbox = sandbox
        self.github_token = github_token
        self.max_lines = max_lines
        self.max_repo_mb = max_repo_mb
        self.http = http

    async def _step(self, emit: Emit, key: str, state: str, **extra: Any) -> None:
        label = dict(STEPS)[key]
        await emit("step", {"key": key, "label": label, "state": state, **extra})

    async def _vitals(self, ref: RepoRef, repo_dir: Path, warnings: list[str]) -> VitalRecords:
        local_last = await last_commit_date(repo_dir)
        try:
            async with GitHubClient(self.github_token) as gh:
                vitals = await gh.vitals(ref)
        except (GitHubError, httpx.HTTPError) as exc:
            warnings.append(f"GitHub API unavailable ({exc}); using dates from the clone.")
            vitals = VitalRecords(
                full_name=ref.full_name,
                url=ref.html_url,
                created_at=await first_commit_date(repo_dir),
                api_available=False,
            )
        if local_last and (vitals.last_commit_at is None or vitals.last_commit_at < local_last):
            vitals.last_commit_at = local_last
        return vitals

    async def _toxicology(
        self, repo_dir: Path, warnings: list[str]
    ) -> tuple[list[Dependency], list[Any]]:
        declared = find_dependencies(repo_dir)
        dependencies, pypi_warnings = await check_dependencies(declared, client=self.http)
        warnings.extend(pypi_warnings)
        pinned = [
            (d.canonical, d.pinned_version or d.minimum_version)
            for d in declared
            if d.pinned_version or d.minimum_version
        ]
        try:
            vulns = await scan_vulnerabilities([(n, v) for n, v in pinned if v], client=self.http)
        except httpx.HTTPError as exc:
            warnings.append(f"OSV lookup failed: {type(exc).__name__}")
            vulns = []
        return dependencies, vulns

    async def run(
        self, job_id: str, ref: RepoRef, workspace: Workspace, emit: Emit = _noop
    ) -> DeathCertificate:
        started = time.monotonic()
        warnings: list[str] = []

        await self._step(emit, "exhume", "running")
        workspace.prepare()
        await clone_repo(ref, workspace.before, max_mb=self.max_repo_mb)
        await self._step(emit, "exhume", "done")

        await self._step(emit, "measure", "running")
        count = await asyncio.to_thread(count_python_lines, workspace.before)
        enforce_limits(count, self.max_lines)
        await self._step(
            emit, "measure", "done", detail=f"{count.lines:,} lines in {count.files} files"
        )

        repo_dir = workspace.before
        reqs = requirement_files(repo_dir)

        async def records() -> VitalRecords:
            await self._step(emit, "records", "running")
            vitals = await self._vitals(ref, repo_dir, warnings)
            await self._step(emit, "records", "done")
            return vitals

        async def examine() -> MarkerScan:
            await self._step(emit, "examine", "running")
            scan = await asyncio.to_thread(scan_repo, repo_dir)
            await self._step(
                emit,
                "examine",
                "done",
                detail=f"{len(scan.markers)} markers, {len(scan.unparseable)} unparseable files",
            )
            return scan

        async def toxicology() -> tuple[list[Dependency], list[Any]]:
            await self._step(emit, "toxicology", "running")
            deps, vulns = await self._toxicology(repo_dir, warnings)
            await self._step(
                emit,
                "toxicology",
                "done",
                detail=f"{len(deps)} dependencies, {len(vulns)} vulnerabilities",
            )
            return deps, vulns

        async def probe() -> RunResult:
            await self._step(emit, "probe", "running")
            result = await self.sandbox.probe(job_id, repo_dir, reqs)
            await self._step(emit, "probe", "done", detail=result.status.value)
            return result

        vitals, scan, (dependencies, vulns), probe_result = await asyncio.gather(
            records(), examine(), toxicology(), probe()
        )
        if probe_result.reason and probe_result.status.value == "skipped":
            warnings.append(f"Install probe skipped: {probe_result.reason}.")

        await self._step(emit, "verdict", "running")
        score, label, breakdown = compute_decay(
            DecayInputs(
                last_commit_at=vitals.last_commit_at,
                archived=vitals.archived,
                files=scan.files,
                markers=scan.markers,
                vulnerabilities=vulns,
                dependencies=dependencies,
                probe=probe_result,
            )
        )
        cause, factors = write_verdict(
            files=scan.files,
            markers=scan.markers,
            dependencies=dependencies,
            vulnerabilities=vulns,
            probe=probe_result,
            breakdown=breakdown,
            last_commit_at=vitals.last_commit_at,
            archived=vitals.archived,
        )
        cert = DeathCertificate(
            vitals=vitals,
            python_lines=count.lines,
            python_files=count.files,
            files=scan.files,
            markers=scan.markers[:MAX_MARKERS_IN_CERT],
            marker_counts=scan.counts,
            has_tests=detect_tests(repo_dir),
            dependencies=dependencies,
            vulnerabilities=vulns,
            probe=probe_result,
            decay_score=score,
            decay_label=label,
            decay_breakdown=breakdown,
            cause_of_death=cause,
            contributing_factors=factors,
            warnings=warnings,
            duration_s=round(time.monotonic() - started, 2),
        )
        await self._step(emit, "verdict", "done", detail=f"decay {score}/100: {label}")
        return cert
