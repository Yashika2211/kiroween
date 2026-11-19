"""The resurrection loop: run the plan's tasks, verify in the sandbox, repair until green."""

from __future__ import annotations

import asyncio
import contextlib
from collections.abc import Awaitable, Callable
from pathlib import Path
from typing import Any

from necromancer.autopsy.deps import find_dev_dependencies
from necromancer.autopsy.pypi import classify
from necromancer.models import (
    DeathCertificate,
    Dependency,
    DependencyStatus,
    FileDiff,
    FixSource,
    PlanTask,
    ResurrectionPlan,
    ResurrectionResult,
    RunResult,
    RunStatus,
    TaskKind,
    TaskStatus,
)
from necromancer.resurrection.diffing import make_diff
from necromancer.resurrection.fixers.api import apply_api_fixes
from necromancer.resurrection.fixers.manifests import (
    Change,
    plan_changes,
    rewrite_literal_requirements,
    rewrite_requirements,
    rewrite_setup_cfg,
)
from necromancer.resurrection.fixers.missing import missing_modules, package_for
from necromancer.resurrection.fixers.modernize import pyupgrade
from necromancer.resurrection.fixers.py2to3 import ConversionError, convert
from necromancer.resurrection.llm import LLMFixer, blame_file
from necromancer.resurrection.smoke import discover_modules, generate_tests
from necromancer.ritual.planner import group_by_file, render_tasks
from necromancer.sandbox.runner import SandboxRunner
from necromancer.workspace import Workspace, iter_python_files, read_text, safe_join

Emit = Callable[[str, dict[str, Any]], Awaitable[None]]

MAX_MISSING_DEP_ROUNDS = 2


async def _noop(_type: str, _data: dict[str, Any]) -> None:
    return None


def requirement_files(root: Path) -> list[str]:
    found: list[str] = []
    for pattern in ("requirements*.txt", "*requirements.txt", "requirements/*.txt"):
        for path in sorted(root.glob(pattern)):
            rel = path.relative_to(root).as_posix()
            if path.is_file() and not path.is_symlink() and "doc" not in rel and rel not in found:
                found.append(rel)
    return found


class Resurrector:
    def __init__(
        self,
        *,
        job_id: str,
        workspace: Workspace,
        certificate: DeathCertificate,
        plan: ResurrectionPlan,
        sandbox: SandboxRunner,
        llm: LLMFixer | None = None,
        max_iterations: int = 3,
        emit: Emit = _noop,
    ) -> None:
        self.job_id = job_id
        self.ws = workspace
        self.cert = certificate
        self.plan = plan
        self.sandbox = sandbox
        self.llm = llm
        self.max_iterations = max_iterations
        self.emit = emit
        self.result = ResurrectionResult()
        self._installed = False

    # ------------------------------------------------------------------ helpers

    @property
    def root(self) -> Path:
        return self.ws.after

    async def log(self, message: str) -> None:
        self.result.notes.append(message)
        await self.emit("log", {"message": message})

    async def _write(self, rel: str, new: str, source: FixSource) -> FileDiff | None:
        path = safe_join(self.root, rel)
        old = read_text(path) if path.exists() else ""
        diff = make_diff(rel, old, new, source)
        if diff is None:
            return None
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(new, encoding="utf-8")
        self.result.diffs.append(diff)
        await self.emit("diff", diff.model_dump())
        return diff

    def _python_files(self) -> list[str]:
        return [p.relative_to(self.root).as_posix() for p in iter_python_files(self.root)]

    async def _set(self, task: PlanTask, status: TaskStatus, note: str = "") -> None:
        task.status = status
        if note:
            task.note = note
        await self.emit("task", task.model_dump())

    # ------------------------------------------------------------------ fixers

    async def _rewrite_py2(self, task: PlanTask) -> str:
        changed = 0
        for rel in task.files:
            path = safe_join(self.root, rel)
            if not path.is_file():
                continue
            source = read_text(path)
            try:
                new = await asyncio.to_thread(convert, source, rel, full=True)
            except ConversionError as exc:
                await self.log(f"2to3 could not parse {rel}: {exc}")
                continue
            if await self._write(rel, new, "py2to3"):
                changed += 1
        return f"{changed} files rewritten"

    async def _modernise(self, task: PlanTask) -> str:
        changed = 0
        legacy = set(group_by_file(self.cert))
        for rel in self._python_files():
            source = read_text(safe_join(self.root, rel))
            new = source
            if rel in legacy:
                with contextlib.suppress(ConversionError):
                    new = await asyncio.to_thread(convert, new, rel, full=False)
            new = await asyncio.to_thread(pyupgrade, new)
            if await self._write(rel, new, "pyupgrade"):
                changed += 1
        return f"{changed} files modernised"

    async def _api(self, task: PlanTask) -> str:
        changed = 0
        for rel in self._python_files():
            source = read_text(safe_join(self.root, rel))
            new, applied = apply_api_fixes(source)
            if applied and await self._write(rel, new, "api"):
                changed += 1
        return f"{changed} files patched"

    def _dev_changes(self) -> dict[str, Change]:
        dead: list[Dependency] = []
        for dep in find_dev_dependencies(self.root):
            classified = classify(dep, None)
            if classified.status is DependencyStatus.DEAD:
                dead.append(classified)
        return plan_changes(dead, [])

    async def _manifests(self, task: PlanTask, source: FixSource) -> str:
        changes = plan_changes(self.cert.dependencies, self.cert.vulnerabilities)
        dev_changes = {**changes, **self._dev_changes()}
        notes: list[str] = []
        for rel in requirement_files(self.root):
            is_dev = any(w in rel for w in ("dev", "test"))
            text = read_text(safe_join(self.root, rel))
            new, file_notes = rewrite_requirements(text, dev_changes if is_dev else changes)
            if await self._write(rel, new, source):
                notes.extend(file_notes)
        for rel, rewriter in (
            ("setup.py", rewrite_literal_requirements),
            ("pyproject.toml", rewrite_literal_requirements),
            ("setup.cfg", rewrite_setup_cfg),
        ):
            path = self.root / rel
            if path.is_file() and not path.is_symlink():
                new, file_notes = rewriter(read_text(path), changes)
                if await self._write(rel, new, source):
                    notes.extend(file_notes)
        for note in dict.fromkeys(notes):
            await self.log(f"dependency: {note}")
        return f"{len(set(notes))} dependency changes"

    async def _tests(self, task: PlanTask) -> str:
        generated = await asyncio.to_thread(generate_tests, self.ws.before, self.root)
        for rel, content in generated.files.items():
            await self._write(rel, content, "smoke")
        self.result.generated_tests = sorted(generated.files)
        return (
            f"{len(generated.modules)} modules smoke-tested, "
            f"{len(generated.properties)} property tests"
        )

    # ------------------------------------------------------------------ sandbox

    async def _install(self) -> RunResult:
        await self.log("Installing on Python 3.12 inside the sandbox…")
        result = await self.sandbox.install(self.job_id, self.root, requirement_files(self.root))
        self.result.install = result
        self._installed = True
        await self.emit("test", {"phase": "install", **result.model_dump()})
        return result

    async def _test(self) -> RunResult:
        await self.log("Running tests in the sandbox (network off)…")
        result = await self.sandbox.test(self.job_id, self.root)
        self.result.tests = result
        await self.emit("test", {"phase": "test", **result.model_dump()})
        return result

    def _local_modules(self) -> set[str]:
        names = {m.split(".")[0] for m in discover_modules(self.root)}
        names |= {p.name for p in self.root.iterdir() if p.is_dir()}
        return names

    async def _add_missing_dependencies(self, output: str) -> bool:
        packages = [
            pkg
            for mod in missing_modules(output)
            if (pkg := package_for(mod, self._local_modules())) is not None
        ]
        if not packages:
            return False
        target = (
            "requirements.txt"
            if (self.root / "requirements.txt").exists()
            else ("requirements-test.txt")
        )
        path = self.root / target
        old = read_text(path) if path.exists() else ""
        existing = {line.strip().lower() for line in old.splitlines()}
        additions = [p for p in packages if p.lower() not in existing]
        if not additions:
            return False
        new = old + ("" if not old or old.endswith("\n") else "\n") + "\n".join(additions) + "\n"
        await self._write(target, new, "deps")
        await self.log(f"Added missing dependencies to {target}: {', '.join(additions)}")
        return True

    async def _verify(self) -> RunResult:
        install = await self._install()
        if install.status is RunStatus.SKIPPED:
            return install
        tests = await self._test()
        rounds = 0
        while not tests.ok and rounds < MAX_MISSING_DEP_ROUNDS:
            if not await self._add_missing_dependencies(tests.tail + "\n" + install.tail):
                break
            rounds += 1
            install = await self._install()
            tests = await self._test()
        if tests.ok and not install.ok:
            last_line = next(
                (ln.strip() for ln in reversed(install.tail.splitlines()) if ln.strip()), ""
            )
            await self.log(
                "Tests pass when run from source, but installing the package itself still "
                f"fails ({last_line[:160]}). This needs a manual look."
            )
        return tests

    async def _llm_loop(self, task: PlanTask, last: RunResult) -> str:
        if self.llm is None:
            return "LLM disabled"
        if last.status is RunStatus.SKIPPED:
            return "sandbox unavailable, cannot verify LLM fixes"
        notes_by_file = group_by_file(self.cert)
        tests = last
        attempts = 0
        tried: dict[str, int] = {}
        while not tests.ok and attempts < self.max_iterations:
            candidates = set(self._python_files())
            target = blame_file(tests.tail, candidates)
            if target is None:
                await self.log("Could not tell which file caused the failure; stopping.")
                break
            if tried.get(target, 0) >= 2:
                await self.log(f"Already tried {target} twice; stopping.")
                break
            tried[target] = tried.get(target, 0) + 1
            attempts += 1
            self.result.iterations = attempts
            await self.log(f"Pass {attempts}: asking Claude to repair {target}")
            source = read_text(safe_join(self.root, target))
            fix = await self.llm.fix_file(
                target,
                source,
                tests.tail,
                [k.replace("_", " ") for k in notes_by_file.get(target, [])],
            )
            if fix is None:
                await self.log(f"No usable fix for {target}.")
                continue
            await self._write(target, fix.new_source, "llm")
            if fix.explanation:
                await self.log(f"Claude: {fix.explanation}")
            tests = await self._test()
        return "tests pass" if tests.ok else f"{attempts} passes, tests still failing"

    # ------------------------------------------------------------------ main

    async def run(self) -> ResurrectionResult:
        await self.log("Copying the remains into a working grave…")
        await asyncio.to_thread(self.ws.fork_working_copy)
        last: RunResult | None = None
        manifests_done = False
        try:
            for task in self.plan.tasks:
                await self._set(task, TaskStatus.RUNNING)
                try:
                    if task.kind is TaskKind.REWRITE and "2to3" in task.title:
                        note = await self._rewrite_py2(task)
                    elif task.kind is TaskKind.REWRITE:
                        note = await self._modernise(task)
                    elif task.kind is TaskKind.API:
                        note = await self._api(task)
                    elif task.kind in (TaskKind.DEPS, TaskKind.VULNS):
                        if manifests_done:
                            note = "covered by the dependency bump"
                        else:
                            note = await self._manifests(
                                task, "deps" if task.kind is TaskKind.DEPS else "vulns"
                            )
                            manifests_done = True
                    elif task.kind is TaskKind.TESTS:
                        note = await self._tests(task)
                    elif task.kind is TaskKind.VERIFY:
                        last = await self._verify()
                        note = last.reason or last.status.value
                        if last.status is RunStatus.SKIPPED:
                            await self._set(task, TaskStatus.SKIPPED, note)
                            continue
                        if not last.ok:
                            await self._set(task, TaskStatus.FAILED, note)
                            continue
                    elif task.kind is TaskKind.LLM:
                        if last is not None and last.ok:
                            await self._set(task, TaskStatus.SKIPPED, "tests already pass")
                            continue
                        note = await self._llm_loop(
                            task, last or RunResult(status=RunStatus.SKIPPED)
                        )
                        ok = self.result.tests is not None and self.result.tests.ok
                        if ok:
                            # The verify task can now be marked done too.
                            for t in self.plan.tasks:
                                if t.kind is TaskKind.VERIFY and t.status is TaskStatus.FAILED:
                                    await self._set(t, TaskStatus.DONE, "passing after repair")
                        await self._set(task, TaskStatus.DONE if ok else TaskStatus.FAILED, note)
                        continue
                    else:
                        note = "unknown task"
                except Exception as exc:  # a broken task must not kill the whole ritual
                    await self._set(task, TaskStatus.FAILED, f"{type(exc).__name__}: {exc}")
                    continue
                await self._set(task, TaskStatus.DONE, note)
            await self._write_plan()
        finally:
            await self.sandbox.cleanup(self.job_id)
        self.result.files_changed = len({d.path for d in self.result.diffs})
        return self.result

    async def _write_plan(self) -> None:
        self.plan.tasks_md = render_tasks(self.cert, self.plan.tasks)
        plan_dir = self.root / ".necromancer" / "plan"
        plan_dir.mkdir(parents=True, exist_ok=True)
        (plan_dir / "requirements.md").write_text(self.plan.requirements_md)
        (plan_dir / "design.md").write_text(self.plan.design_md)
        (plan_dir / "tasks.md").write_text(self.plan.tasks_md)
