"""Decay score: 0 (healthy) to 100 (fully decomposed), with a visible breakdown."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import UTC, datetime

from necromancer.models import (
    DecayFactor,
    Dependency,
    DependencyStatus,
    FileHealth,
    Marker,
    RunResult,
    RunStatus,
    Severity,
    Vulnerability,
)

# Weights live here as data so the UI and the docs can show them.
WEIGHTS = {
    "age": 25.0,
    "archived": 10.0,
    "syntax": 25.0,
    "markers": 15.0,
    "vulns": 15.0,
    "deps": 10.0,
    "install": 10.0,
}

LABELS = [
    (0, "Freshly buried"),
    (20, "Restless"),
    (40, "Decomposing"),
    (60, "Skeletal"),
    (80, "Dust"),
]


@dataclass(frozen=True)
class DecayInputs:
    last_commit_at: datetime | None
    archived: bool | None
    files: list[FileHealth]
    markers: list[Marker]
    vulnerabilities: list[Vulnerability]
    dependencies: list[Dependency]
    probe: RunResult | None
    now: datetime | None = None


def label_for(score: float) -> str:
    label = LABELS[0][1]
    for threshold, name in LABELS:
        if score >= threshold:
            label = name
    return label


def _years_since(when: datetime | None, now: datetime) -> float:
    if when is None:
        return 0.0
    if when.tzinfo is None:
        when = when.replace(tzinfo=UTC)
    return max(0.0, (now - when).days / 365.25)


def compute_decay(inputs: DecayInputs) -> tuple[int, str, list[DecayFactor]]:
    now = inputs.now or datetime.now(UTC)
    factors: list[DecayFactor] = []

    years = _years_since(inputs.last_commit_at, now)
    factors.append(
        DecayFactor(
            key="age",
            label="Time in the grave",
            points=min(WEIGHTS["age"], 5 * years),
            max_points=WEIGHTS["age"],
            detail=f"{years:.1f} years since the last commit"
            if inputs.last_commit_at
            else "last commit unknown",
        )
    )

    factors.append(
        DecayFactor(
            key="archived",
            label="Archived",
            points=WEIGHTS["archived"] if inputs.archived else 0.0,
            max_points=WEIGHTS["archived"],
            detail="the owner archived the repository" if inputs.archived else "not archived",
        )
    )

    total = len(inputs.files) or 1
    failing = sum(1 for f in inputs.files if not f.parses)
    factors.append(
        DecayFactor(
            key="syntax",
            label="Won't parse on 3.12",
            points=min(WEIGHTS["syntax"], 50 * failing / total),
            max_points=WEIGHTS["syntax"],
            detail=f"{failing} of {len(inputs.files)} files are syntax errors on Python 3.12",
        )
    )

    marker_count = len(inputs.markers)
    factors.append(
        DecayFactor(
            key="markers",
            label="Legacy idioms",
            points=min(WEIGHTS["markers"], marker_count / 2),
            max_points=WEIGHTS["markers"],
            detail=f"{marker_count} Python 2 / removed-API markers",
        )
    )

    weighted_vulns = sum(
        2 if v.severity in (Severity.CRITICAL, Severity.HIGH) else 1 for v in inputs.vulnerabilities
    )
    factors.append(
        DecayFactor(
            key="vulns",
            label="Known vulnerabilities",
            points=min(WEIGHTS["vulns"], 3 * weighted_vulns),
            max_points=WEIGHTS["vulns"],
            detail=f"{len(inputs.vulnerabilities)} known vulnerabilities in pinned dependencies",
        )
    )

    dead = sum(
        1
        for d in inputs.dependencies
        if d.status in (DependencyStatus.DEAD, DependencyStatus.MISSING)
    )
    factors.append(
        DecayFactor(
            key="deps",
            label="Dead dependencies",
            points=min(WEIGHTS["deps"], 5 * dead),
            max_points=WEIGHTS["deps"],
            detail=f"{dead} dependencies are dead, renamed or missing from PyPI",
        )
    )

    probe_failed = inputs.probe is not None and inputs.probe.status in (
        RunStatus.FAILED,
        RunStatus.TIMEOUT,
    )
    factors.append(
        DecayFactor(
            key="install",
            label="Fails to install",
            points=WEIGHTS["install"] if probe_failed else 0.0,
            max_points=WEIGHTS["install"],
            detail=(
                "pip install fails on Python 3.12"
                if probe_failed
                else "install probe skipped"
                if inputs.probe is None or inputs.probe.status is RunStatus.SKIPPED
                else "installs on Python 3.12"
            ),
        )
    )

    for f in factors:
        f.points = round(f.points, 1)
    score = round(min(100.0, sum(f.points for f in factors)))
    return score, label_for(score), factors
