from datetime import UTC, datetime

from hypothesis import given
from hypothesis import strategies as st

from necromancer.autopsy.decay import WEIGHTS, DecayInputs, compute_decay, label_for
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

NOW = datetime(2026, 11, 1, tzinfo=UTC)


def test_healthy_repo_scores_zero() -> None:
    score, label, factors = compute_decay(
        DecayInputs(
            last_commit_at=NOW,
            archived=False,
            files=[FileHealth(path="a.py", lines=10, parses=True)],
            markers=[],
            vulnerabilities=[],
            dependencies=[],
            probe=RunResult(status=RunStatus.PASSED),
            now=NOW,
        )
    )
    assert score == 0
    assert label == "Freshly buried"
    assert {f.key for f in factors} == set(WEIGHTS)


def test_dead_repo_scores_high() -> None:
    marker = Marker(
        file="a.py", line=1, kind="print_statement", category=MarkerCategory.SYNTAX, excerpt=""
    )
    score, label, _ = compute_decay(
        DecayInputs(
            last_commit_at=datetime(2013, 3, 12, tzinfo=UTC),
            archived=True,
            files=[FileHealth(path="a.py", lines=10, parses=False)],
            markers=[marker] * 40,
            vulnerabilities=[Vulnerability(id="X", package="numpy", severity=Severity.HIGH)] * 3,
            dependencies=[Dependency(name="nose", source="r", status=DependencyStatus.DEAD)] * 2,
            probe=RunResult(status=RunStatus.FAILED),
            now=NOW,
        )
    )
    assert score == 100
    assert label == "Dust"


def test_naive_datetimes_are_treated_as_utc() -> None:
    score, _, factors = compute_decay(
        DecayInputs(datetime(2024, 11, 1), None, [], [], [], [], None, now=NOW)
    )
    assert factors[0].points == 10.0
    assert score == 10


def test_labels() -> None:
    assert [label_for(s) for s in (0, 19, 20, 45, 60, 99)] == [
        "Freshly buried",
        "Freshly buried",
        "Restless",
        "Decomposing",
        "Skeletal",
        "Dust",
    ]


@given(
    years=st.floats(0, 50),
    archived=st.booleans() | st.none(),
    parses=st.lists(st.booleans(), max_size=30),
    markers=st.integers(0, 500),
    vulns=st.integers(0, 50),
)
def test_score_is_bounded_and_matches_breakdown(
    years: float, archived: bool | None, parses: list[bool], markers: int, vulns: int
) -> None:
    when = datetime.fromtimestamp(NOW.timestamp() - years * 365.25 * 86400, tz=UTC)
    m = Marker(file="a.py", line=1, kind="x", category=MarkerCategory.API, excerpt="")
    score, _, factors = compute_decay(
        DecayInputs(
            last_commit_at=when,
            archived=archived,
            files=[FileHealth(path=f"{i}.py", lines=1, parses=p) for i, p in enumerate(parses)],
            markers=[m] * markers,
            vulnerabilities=[Vulnerability(id="v", package="p")] * vulns,
            dependencies=[],
            probe=None,
            now=NOW,
        )
    )
    assert 0 <= score <= 100
    for f in factors:
        assert 0 <= f.points <= f.max_points
    assert abs(score - min(100, sum(f.points for f in factors))) <= 1
