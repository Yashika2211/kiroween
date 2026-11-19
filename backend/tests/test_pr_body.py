from necromancer.models import FileDiff, ResurrectionResult, RunResult, RunStatus, TaskStatus
from necromancer.rise.pr_body import pr_title, render_pr_body
from necromancer.ritual.planner import build_plan
from tests.factories import certificate
from tests.test_planner import check_snapshot


def make_result(ok: bool) -> ResurrectionResult:
    return ResurrectionResult(
        tests=RunResult(
            status=RunStatus.PASSED if ok else RunStatus.FAILED,
            tail="5 passed in 0.3s" if ok else "E boom",
        ),
        diffs=[
            FileDiff(path="deadrepo/core.py", source="py2to3", diff=""),
            FileDiff(path="deadrepo/core.py", source="pyupgrade", diff=""),
            FileDiff(path="requirements.txt", source="deps", diff=""),
        ],
        files_changed=2,
        generated_tests=["tests/test_necromancer_smoke.py"],
        notes=["dependency: nose: nose is dead; replaced by pytest"],
    )


def test_title() -> None:
    assert pr_title(certificate(), make_result(True)).endswith("(tests passing)")
    assert pr_title(certificate(), make_result(False)).endswith("(tests needs review)")


def test_body_snapshot() -> None:
    cert = certificate()
    plan = build_plan(cert)
    for t in plan.tasks:
        t.status = TaskStatus.DONE
    plan.tasks[-1].status = TaskStatus.SKIPPED
    plan.tasks[-1].note = "tests already pass"
    body = render_pr_body(cert, plan, make_result(True))
    assert "✅ Tests pass on Python 3.12" in body
    assert "`5 passed in 0.3s`" in body
    assert "nose is dead; replaced by pytest" in body
    check_snapshot("pr_body.md", body)


def test_failing_body_includes_output() -> None:
    body = render_pr_body(certificate(), build_plan(certificate()), make_result(False))
    assert "❌ Tests still fail" in body and "E boom" in body
