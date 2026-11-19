"""Turn a Death Certificate into a Kiro-style resurrection spec.

Deterministic: the same certificate always produces the same plan.
"""

from __future__ import annotations

from collections import defaultdict
from dataclasses import dataclass, field

from necromancer.models import (
    DeathCertificate,
    DependencyStatus,
    MarkerCategory,
    PlanTask,
    ResurrectionPlan,
    TaskKind,
)


@dataclass
class ProblemClass:
    key: str
    req_id: str
    title: str
    story: str
    criteria: list[str]
    strategy: str
    files: list[str] = field(default_factory=list)
    detail: list[str] = field(default_factory=list)


def _files_with(cert: DeathCertificate, categories: set[MarkerCategory]) -> list[str]:
    return sorted({m.file for m in cert.markers if m.category in categories})


def classify(cert: DeathCertificate, *, llm_enabled: bool = True) -> list[ProblemClass]:
    classes: list[ProblemClass] = []
    n = 0

    def next_id() -> str:
        nonlocal n
        n += 1
        return str(n)

    unparseable = [f.path for f in cert.files if not f.parses]
    if unparseable:
        kinds = sorted(
            {
                m.kind
                for m in cert.markers
                if m.category is MarkerCategory.SYNTAX and m.file in unparseable
            }
        )
        classes.append(
            ProblemClass(
                key="syntax",
                req_id=next_id(),
                title="Python 3.12 syntax",
                story="As a user, I want every module to parse on Python 3.12 so that it can be imported.",
                criteria=[
                    "WHEN any module is parsed with Python 3.12 THEN it SHALL NOT raise SyntaxError.",
                    "WHEN Python 2 constructs are rewritten THEN behaviour SHALL be preserved.",
                ],
                strategy="Run the 2to3 fixers (via `fissix`, a maintained lib2to3 fork) on the files "
                "that fail to parse. This is a static text transform; no repository code runs.",
                files=unparseable,
                detail=[f"constructs: {', '.join(k.replace('_', ' ') for k in kinds)}"]
                if kinds
                else [],
            )
        )

    idiom_files = _files_with(cert, {MarkerCategory.BUILTIN})
    classes.append(
        ProblemClass(
            key="idioms",
            req_id=next_id(),
            title="Modern idioms",
            story="As a maintainer, I want the code to use current Python idioms so it is easy to keep alive.",
            criteria=[
                "WHEN the code uses removed builtins (xrange, iteritems, basestring, ...) THEN they SHALL "
                "be replaced with their Python 3 equivalents.",
                "WHEN pyupgrade --py312-plus runs on the result THEN it SHALL make no further changes.",
            ],
            strategy="Run `pyupgrade --py312-plus` over every module after the syntax pass.",
            files=idiom_files,
            detail=[
                f"{len(idiom_files)} file{'' if len(idiom_files) == 1 else 's'} use removed builtins"
            ]
            if idiom_files
            else [],
        )
    )

    api_files = _files_with(cert, {MarkerCategory.STDLIB, MarkerCategory.API})
    if api_files:
        kinds = sorted(
            {
                m.kind
                for m in cert.markers
                if m.category in {MarkerCategory.STDLIB, MarkerCategory.API}
            }
        )
        classes.append(
            ProblemClass(
                key="api",
                req_id=next_id(),
                title="Removed standard-library modules and APIs",
                story="As a user, I want imports and API calls to resolve on Python 3.12.",
                criteria=[
                    "WHEN a module imports a renamed or removed stdlib module THEN the import SHALL be "
                    "rewritten to the current location.",
                    "WHEN a removed API has a drop-in replacement THEN it SHALL be substituted.",
                ],
                strategy="Apply Necromancer's replacement table (collections.abc, base64.encodebytes, "
                "unittest aliases, ...). Cases without a safe mechanical fix go to the LLM pass.",
                files=api_files,
                detail=[f"issues: {', '.join(k.replace('_', ' ') for k in kinds)}"],
            )
        )

    dep_issues = [
        d
        for d in cert.dependencies
        if d.status
        in {
            DependencyStatus.OUTDATED,
            DependencyStatus.DEAD,
            DependencyStatus.MISSING,
            DependencyStatus.UNPINNED,
        }
    ]
    if dep_issues:
        detail = []
        for d in dep_issues:
            if d.status is DependencyStatus.DEAD:
                target = d.replacement or "the standard library"
                detail.append(f"`{d.name}` is dead → {target}")
            elif d.status is DependencyStatus.OUTDATED:
                detail.append(f"`{d.name}` {d.pinned_version} → {d.latest}")
            elif d.status is DependencyStatus.UNPINNED:
                detail.append(
                    f"`{d.name}` is unpinned → `>={d.latest}`"
                    if d.latest
                    else f"`{d.name}` is unpinned"
                )
            else:
                detail.append(f"`{d.name}` is missing from PyPI")
        classes.append(
            ProblemClass(
                key="deps",
                req_id=next_id(),
                title="Installable dependencies",
                story="As a user, I want `pip install` to succeed on Python 3.12.",
                criteria=[
                    "WHEN dependencies are installed on Python 3.12 THEN pip SHALL exit with status 0.",
                    "WHEN a dependency is dead THEN it SHALL be replaced by its successor or removed if "
                    "the standard library covers it.",
                ],
                strategy="Rewrite requirement manifests in place (keeping comments and order): bump pins "
                "to the newest release that supports 3.12, swap dead packages for successors.",
                files=sorted({d.source for d in dep_issues}),
                detail=detail,
            )
        )

    if cert.vulnerabilities:
        detail = [
            f"{v.id} ({v.severity.value}) in `{v.package}` {v.version or ''} → fixed in {v.fixed or 'n/a'}"
            for v in cert.vulnerabilities[:12]
        ]
        classes.append(
            ProblemClass(
                key="vulns",
                req_id=next_id(),
                title="No known vulnerabilities",
                story="As a security-conscious user, I want no dependency with a known advisory.",
                criteria=[
                    "WHEN dependencies are queried against OSV THEN no pinned version SHALL have a known "
                    "vulnerability with an available fix.",
                ],
                strategy="Raise each vulnerable pin to at least its OSV fixed version (the dependency "
                "bump usually covers this).",
                files=sorted({d.source for d in cert.dependencies}),
                detail=detail,
            )
        )

    classes.append(
        ProblemClass(
            key="tests",
            req_id=next_id(),
            title="Proof of life",
            story="As a maintainer, I want automated evidence that the resurrected code works.",
            criteria=[
                "WHEN the test suite runs in the sandbox THEN it SHALL pass.",
                "IF the repository has no tests THEN smoke tests SHALL import every module.",
                "WHERE pure functions exist THEN property tests SHALL show the resurrected function "
                "matches the original on generated inputs.",
            ],
            strategy=(
                "Run the existing suite with pytest inside the sandbox (no network)."
                if cert.has_tests
                else "Generate `tests/test_necromancer_smoke.py` that imports every module, then run it."
            )
            + (
                " If anything still fails, ask the LLM to repair one file at a time (max passes from config)."
                if llm_enabled
                else " LLM repair is disabled, so remaining failures are reported in the pull request."
            ),
            files=[],
        )
    )
    return classes


def plan_tasks(
    cert: DeathCertificate, classes: list[ProblemClass], *, llm_enabled: bool
) -> list[PlanTask]:
    by_key = {c.key: c for c in classes}
    tasks: list[PlanTask] = []

    def add(kind: TaskKind, title: str, cls: str, files: list[str] | None = None) -> None:
        req = by_key[cls].req_id if cls in by_key else None
        tasks.append(
            PlanTask(
                id=str(len(tasks) + 1),
                title=title,
                kind=kind,
                files=files or [],
                requirement_ids=[req] if req else [],
            )
        )

    if "syntax" in by_key:
        add(
            TaskKind.REWRITE,
            "Rewrite Python 2 syntax with 2to3 fixers",
            "syntax",
            by_key["syntax"].files,
        )
    add(
        TaskKind.REWRITE,
        "Modernise idioms with pyupgrade --py312-plus",
        "idioms",
        by_key["idioms"].files,
    )
    if "api" in by_key:
        add(TaskKind.API, "Replace removed stdlib modules and APIs", "api", by_key["api"].files)
    if "deps" in by_key:
        add(TaskKind.DEPS, "Bump and replace dependencies", "deps", by_key["deps"].files)
    if "vulns" in by_key:
        add(
            TaskKind.VULNS,
            "Raise vulnerable pins to fixed versions",
            "vulns",
            by_key["vulns"].files,
        )
    add(
        TaskKind.TESTS,
        "Add smoke tests" + (" and property tests" if cert.has_tests else " (no tests found)"),
        "tests",
    )
    add(TaskKind.VERIFY, "Install on Python 3.12 and run tests in the sandbox", "tests")
    if llm_enabled:
        add(TaskKind.LLM, "Repair remaining failures with the LLM, one file at a time", "tests")
    return tasks


def render_requirements(cert: DeathCertificate, classes: list[ProblemClass]) -> str:
    lines = [
        f"# Requirements: Resurrect {cert.vitals.full_name}",
        "",
        "## Introduction",
        "",
        f"**Cause of death:** {cert.cause_of_death}",
        "",
        f"Decay score {cert.decay_score}/100 ({cert.decay_label}). "
        f"{cert.python_lines:,} lines of Python across {cert.python_files} files.",
        "",
        "## Requirements",
    ]
    for c in classes:
        lines += [
            "",
            f"### Requirement {c.req_id}: {c.title}",
            "",
            f"**User story:** {c.story}",
            "",
        ]
        lines += ["#### Acceptance criteria", ""]
        lines += [f"{i}. {crit}" for i, crit in enumerate(c.criteria, start=1)]
    return "\n".join(lines) + "\n"


def render_design(cert: DeathCertificate, classes: list[ProblemClass]) -> str:
    lines = [
        f"# Design: Resurrect {cert.vitals.full_name}",
        "",
        "## Approach",
        "",
        "Deterministic fixes run first, in order, each on the output of the previous one. Every "
        "change is recorded as a unified diff. Repository code only ever runs inside the Docker "
        "sandbox (network off for tests).",
        "",
        "```",
        "2to3 fixers → pyupgrade → API table → manifests → smoke tests → sandbox → (LLM loop)",
        "```",
    ]
    for c in classes:
        lines += ["", f"## {c.title} (Requirement {c.req_id})", "", c.strategy]
        if c.detail:
            lines += [""] + [f"- {d}" for d in c.detail]
        if c.files:
            shown = c.files[:15]
            lines += ["", "Files: " + ", ".join(f"`{f}`" for f in shown)]
            if len(c.files) > len(shown):
                lines[-1] += f" and {len(c.files) - len(shown)} more"
    return "\n".join(lines) + "\n"


def render_tasks(cert: DeathCertificate, tasks: list[PlanTask]) -> str:
    lines = [f"# Tasks: Resurrect {cert.vitals.full_name}", ""]
    for t in tasks:
        box = "x" if t.status.value == "done" else " "
        reqs = ", ".join(t.requirement_ids)
        lines.append(f"- [{box}] {t.id}. {t.title}" + (f" (_Req {reqs}_)" if reqs else ""))
        if t.files:
            shown = ", ".join(f"`{f}`" for f in t.files[:6])
            more = f" +{len(t.files) - 6} more" if len(t.files) > 6 else ""
            lines.append(f"  - files: {shown}{more}")
    return "\n".join(lines) + "\n"


def build_plan(cert: DeathCertificate, *, llm_enabled: bool = True) -> ResurrectionPlan:
    classes = classify(cert, llm_enabled=llm_enabled)
    tasks = plan_tasks(cert, classes, llm_enabled=llm_enabled)
    return ResurrectionPlan(
        requirements_md=render_requirements(cert, classes),
        design_md=render_design(cert, classes),
        tasks_md=render_tasks(cert, tasks),
        tasks=tasks,
    )


def group_by_file(cert: DeathCertificate) -> dict[str, list[str]]:
    """Marker kinds per file, handy for prompts and the PR body."""
    grouped: dict[str, set[str]] = defaultdict(set)
    for m in cert.markers:
        grouped[m.file].add(m.kind)
    return {k: sorted(v) for k, v in sorted(grouped.items())}
