from datetime import UTC, datetime

from necromancer.autopsy.decay import DecayInputs, compute_decay
from necromancer.autopsy.verdict import write_verdict
from necromancer.models import (
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


def verdict(**kw):
    defaults = dict(
        files=[FileHealth(path="a.py", lines=1, parses=True)],
        markers=[],
        dependencies=[],
        vulnerabilities=[],
        probe=None,
        last_commit_at=datetime(2014, 8, 1, tzinfo=UTC),
        archived=False,
    )
    defaults.update(kw)
    _, _, breakdown = compute_decay(
        DecayInputs(
            defaults["last_commit_at"],
            defaults["archived"],
            defaults["files"],
            defaults["markers"],
            defaults["vulnerabilities"],
            defaults["dependencies"],
            defaults["probe"],
        )
    )
    return write_verdict(breakdown=breakdown, **defaults)


def test_python2_syntax_is_primary_cause() -> None:
    cause, factors = verdict(
        files=[FileHealth(path="a.py", lines=1, parses=False)],
        markers=[
            Marker(
                file="a.py",
                line=1,
                kind="print_statement",
                category=MarkerCategory.SYNTAX,
                excerpt="",
            )
        ],
    )
    assert cause.startswith("Acute Python 2 syndrome: 1 file no longer parse")
    assert "print statement" in cause
    assert any("No commits for" in f for f in factors)


def test_dependency_rot() -> None:
    cause, factors = verdict(
        dependencies=[
            Dependency(
                name="numpy", pinned_version="1.8.1", source="r", status=DependencyStatus.OUTDATED
            )
        ],
        probe=RunResult(status=RunStatus.FAILED),
    )
    assert cause.startswith("Dependency rot: pinned to numpy 1.8.1")
    assert "pip install fails on Python 3.12." in factors


def test_poisoned_by_vulns() -> None:
    cause, _ = verdict(
        vulnerabilities=[Vulnerability(id="x", package="p", severity=Severity.CRITICAL)]
    )
    assert cause.startswith("Poisoned")


def test_removed_stdlib() -> None:
    cause, _ = verdict(
        markers=[
            Marker(
                file="a.py",
                line=1,
                kind="removed_module",
                category=MarkerCategory.STDLIB,
                excerpt="import imp",
            )
        ]
    )
    assert "imp" in cause and cause.startswith("Organ failure")


def test_archived_but_healthy() -> None:
    cause, factors = verdict(archived=True)
    assert cause.startswith("Abandoned")
    assert "Repository is archived." in factors
