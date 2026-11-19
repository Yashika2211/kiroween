"""Cause of death: one sentence, plus contributing factors."""

from __future__ import annotations

from datetime import UTC, datetime

from necromancer.models import (
    DecayFactor,
    Dependency,
    DependencyStatus,
    FileHealth,
    Marker,
    MarkerCategory,
    RunResult,
    RunStatus,
    Severity,
    Vulnerability,
)


def _plural(n: int, word: str) -> str:
    return f"{n} {word}{'' if n == 1 else 's'}"


def write_verdict(
    *,
    files: list[FileHealth],
    markers: list[Marker],
    dependencies: list[Dependency],
    vulnerabilities: list[Vulnerability],
    probe: RunResult | None,
    breakdown: list[DecayFactor],
    last_commit_at: datetime | None,
    archived: bool | None,
) -> tuple[str, list[str]]:
    """Return (cause_of_death, contributing_factors)."""
    unparseable = [f for f in files if not f.parses]
    syntax = [m for m in markers if m.category is MarkerCategory.SYNTAX]
    stdlib = [m for m in markers if m.category is MarkerCategory.STDLIB]
    dead = [
        d for d in dependencies if d.status in (DependencyStatus.DEAD, DependencyStatus.MISSING)
    ]
    outdated = [d for d in dependencies if d.status is DependencyStatus.OUTDATED]
    severe = [v for v in vulnerabilities if v.severity in (Severity.CRITICAL, Severity.HIGH)]
    install_failed = probe is not None and probe.status in (RunStatus.FAILED, RunStatus.TIMEOUT)

    # The primary cause is the factor that contributed the most decay, phrased as a diagnosis.
    ranked = sorted(breakdown, key=lambda f: f.points, reverse=True)
    top = ranked[0].key if ranked and ranked[0].points > 0 else None

    if unparseable and (top in {"syntax", "markers", None} or not install_failed):
        cause = (
            f"Acute Python 2 syndrome: {_plural(len(unparseable), 'file')} no longer parse on "
            "Python 3.12"
        )
        if syntax:
            kinds = sorted({m.kind.replace("_", " ") for m in syntax})[:3]
            cause += f" ({', '.join(kinds)})"
        cause += "."
    elif install_failed and outdated:
        names = ", ".join(f"{d.name} {d.pinned_version}" for d in outdated[:3])
        cause = f"Dependency rot: pinned to {names}, which no longer install on Python 3.12."
    elif install_failed:
        cause = "Failed to thrive: the package does not install on Python 3.12."
    elif severe:
        cause = (
            f"Poisoned: {_plural(len(severe), 'high-severity vulnerability')} in pinned "
            "dependencies."
        )
    elif dead:
        cause = f"Starved: depends on {', '.join(d.name for d in dead[:3])}, which no longer exist."
    elif stdlib:
        mods = sorted(
            {m.excerpt.split()[1].split(".")[0] for m in stdlib if len(m.excerpt.split()) > 1}
        )
        cause = f"Organ failure: imports removed standard-library modules ({', '.join(mods[:3])})."
    elif markers:
        cause = f"Slow decay: {_plural(len(markers), 'legacy idiom')} that modern Python rejects."
    elif archived:
        cause = "Abandoned: archived by its owner, though the code itself is still breathing."
    else:
        cause = "Natural causes: neglected, but nothing fatal was found."

    factors: list[str] = []
    if last_commit_at:
        years = (datetime.now(UTC) - last_commit_at).days / 365.25
        if years >= 1:
            factors.append(f"No commits for {years:.0f} years (last: {last_commit_at:%B %Y}).")
    if archived:
        factors.append("Repository is archived.")
    if unparseable:
        factors.append(f"{_plural(len(unparseable), 'file')} fail to parse on Python 3.12.")
    if markers:
        factors.append(f"{_plural(len(markers), 'legacy marker')} found.")
    if outdated:
        factors.append(f"{_plural(len(outdated), 'outdated dependency')} pinned.")
    if dead:
        factors.append(f"Dead dependencies: {', '.join(d.name for d in dead)}.")
    if vulnerabilities:
        factors.append(
            f"{_plural(len(vulnerabilities), 'known vulnerability')} "
            f"({len(severe)} high or critical)."
        )
    if install_failed:
        factors.append("pip install fails on Python 3.12.")
    return cause, factors
