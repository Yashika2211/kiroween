"""Render the pull request title and body. Pure functions, snapshot-tested."""

from __future__ import annotations

from collections import Counter

from necromancer.models import (
    DeathCertificate,
    DependencyStatus,
    ResurrectionPlan,
    ResurrectionResult,
    RunStatus,
    TaskStatus,
)

_TASK_ICON = {
    TaskStatus.DONE: "x",
    TaskStatus.SKIPPED: " ",
    TaskStatus.FAILED: " ",
    TaskStatus.PENDING: " ",
    TaskStatus.RUNNING: " ",
}
_TASK_NOTE = {TaskStatus.SKIPPED: "skipped", TaskStatus.FAILED: "**failed**"}


def pr_title(cert: DeathCertificate, result: ResurrectionResult) -> str:
    state = "passing" if result.tests and result.tests.ok else "needs review"
    return f"Resurrect {cert.vitals.full_name} for Python 3.12 (tests {state})"


def _test_line(result: ResurrectionResult) -> str:
    tests = result.tests
    if tests is None:
        return "Tests were not run."
    if tests.status is RunStatus.PASSED:
        last = next((ln for ln in reversed(tests.tail.splitlines()) if ln.strip()), "")
        return f"✅ Tests pass on Python 3.12 in an isolated sandbox: `{last.strip()}`"
    if tests.status is RunStatus.SKIPPED:
        return f"⚪ Tests were skipped: {tests.reason or 'sandbox unavailable'}."
    return f"❌ Tests still fail ({tests.status.value}). See the log below."


def render_pr_body(
    cert: DeathCertificate, plan: ResurrectionPlan, result: ResurrectionResult
) -> str:
    v = cert.vitals
    born = v.created_at.year if v.created_at else "?"
    died = v.last_commit_at.year if v.last_commit_at else "?"
    lines: list[str] = [
        "## 🪦 Death Certificate",
        "",
        f"**{v.full_name}** ({born} – {died})",
        "",
        f"> **Cause of death:** {cert.cause_of_death}",
        "",
        f"**Decay score:** {cert.decay_score}/100 ({cert.decay_label})",
        "",
        "| Finding | Count |",
        "|---|---|",
        f"| Python files | {cert.python_files} ({cert.python_lines:,} lines) |",
        f"| Files that fail to parse on 3.12 | {len(cert.unparseable_files)} |",
        f"| Legacy markers | {sum(cert.marker_counts.values()) or len(cert.markers)} |",
        f"| Outdated dependencies | {sum(1 for d in cert.dependencies if d.status is DependencyStatus.OUTDATED)} |",
        f"| Dead dependencies | {sum(1 for d in cert.dependencies if d.status is DependencyStatus.DEAD)} |",
        f"| Known vulnerabilities | {len(cert.vulnerabilities)} |",
        "",
    ]
    if cert.contributing_factors:
        lines += ["<details><summary>Contributing factors</summary>", ""]
        lines += [f"- {f}" for f in cert.contributing_factors]
        lines += ["", "</details>", ""]

    lines += ["## 🕯️ The Ritual", ""]
    for t in plan.tasks:
        note = _TASK_NOTE.get(t.status, "")
        extra = (
            f" ({note}{': ' + t.note if t.note else ''})"
            if note
            else (f": {t.note}" if t.note else "")
        )
        lines.append(f"- [{_TASK_ICON[t.status]}] {t.title}{extra}")
    lines.append("")

    lines += ["## 🧟 Resurrection", "", _test_line(result), ""]
    sources = Counter(d.source for d in result.diffs)
    labels = {
        "py2to3": "2to3 fixers (fissix)",
        "pyupgrade": "pyupgrade --py312-plus",
        "api": "removed-API replacements",
        "deps": "dependency manifests",
        "vulns": "vulnerability pins",
        "smoke": "generated tests",
        "llm": "Claude-assisted repairs",
    }
    lines += [f"**{result.files_changed} files changed.** Changes by source:", ""]
    lines += [f"- {labels.get(src, src)}: {n}" for src, n in sources.most_common()]
    lines.append("")
    if result.generated_tests:
        lines += ["Generated tests:", ""] + [f"- `{p}`" for p in result.generated_tests[:6]] + [""]
    dep_notes = [n for n in result.notes if n.startswith("dependency: ")]
    if dep_notes:
        lines += ["<details><summary>Dependency changes</summary>", ""]
        lines += [f"- {n.removeprefix('dependency: ')}" for n in dep_notes]
        lines += ["", "</details>", ""]
    if cert.vulnerabilities:
        lines += ["<details><summary>Vulnerabilities addressed</summary>", ""]
        lines += [
            f"- [{v.id}]({v.url}) {v.severity.value} in `{v.package}` {v.version or ''} → fixed in {v.fixed or 'n/a'}"
            for v in cert.vulnerabilities[:20]
        ]
        lines += ["", "</details>", ""]
    if result.tests and not result.tests.ok and result.tests.tail:
        lines += [
            "<details><summary>Last test output</summary>",
            "",
            "```",
            result.tests.tail[-3000:],
            "```",
            "",
            "</details>",
            "",
        ]
    lines += [
        "The full resurrection spec (requirements, design, tasks) is in `.necromancer/plan/`.",
        "",
        "---",
        "_Raised from the dead by [Necromancer](https://github.com/Yashika2211/kiroween). "
        "Repository code only ran inside a network-isolated Docker sandbox. Please review before merging._",
    ]
    return "\n".join(lines) + "\n"
