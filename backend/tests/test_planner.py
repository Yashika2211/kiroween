import os
from pathlib import Path

from necromancer.models import TaskKind
from necromancer.ritual.planner import build_plan, classify, group_by_file
from tests.factories import certificate

SNAPSHOTS = Path(__file__).parent / "snapshots"


def check_snapshot(name: str, text: str) -> None:
    path = SNAPSHOTS / name
    if os.environ.get("UPDATE_SNAPSHOTS") or not path.exists():
        path.write_text(text)
    assert text == path.read_text(), f"snapshot {name} changed; rerun with UPDATE_SNAPSHOTS=1"


def test_task_order_follows_the_spec() -> None:
    plan = build_plan(certificate())
    assert [t.kind for t in plan.tasks] == [
        TaskKind.REWRITE,
        TaskKind.REWRITE,
        TaskKind.API,
        TaskKind.DEPS,
        TaskKind.VULNS,
        TaskKind.TESTS,
        TaskKind.VERIFY,
        TaskKind.LLM,
    ]
    assert [t.id for t in plan.tasks] == [str(i) for i in range(1, 9)]
    assert plan.tasks[0].files == ["deadrepo/__init__.py", "deadrepo/core.py", "tests/test_core.py"]
    assert all(t.requirement_ids for t in plan.tasks)


def test_empty_classes_are_omitted() -> None:
    cert = certificate(files=[], markers=[], dependencies=[], vulnerabilities=[])
    kinds = [t.kind for t in build_plan(cert, llm_enabled=False).tasks]
    assert kinds == [TaskKind.REWRITE, TaskKind.TESTS, TaskKind.VERIFY]


def test_requirements_use_ears_and_number_sequentially() -> None:
    classes = classify(certificate())
    assert [c.req_id for c in classes] == [str(i) for i in range(1, len(classes) + 1)]
    plan = build_plan(certificate())
    assert (
        "WHEN any module is parsed with Python 3.12 THEN it SHALL NOT raise SyntaxError."
        in plan.requirements_md
    )
    assert "`nose` is dead → pytest" in plan.design_md
    assert "`requests` 2.2.1 → 2.32.3" in plan.design_md


def test_plan_is_deterministic_and_matches_snapshots() -> None:
    a, b = build_plan(certificate()), build_plan(certificate())
    assert a == b
    check_snapshot("plan_requirements.md", a.requirements_md)
    check_snapshot("plan_design.md", a.design_md)
    check_snapshot("plan_tasks.md", a.tasks_md)


def test_group_by_file() -> None:
    grouped = group_by_file(certificate())
    assert grouped["deadrepo/core.py"] == ["dict_iteritems", "print_statement", "removed_module"]
