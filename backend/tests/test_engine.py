import ast
import shutil
from pathlib import Path
from typing import Any

import pytest

from necromancer.autopsy.markers import scan_repo
from necromancer.models import (
    DeathCertificate,
    Dependency,
    DependencyStatus,
    RunResult,
    RunStatus,
    TaskKind,
    TaskStatus,
    VitalRecords,
)
from necromancer.resurrection.engine import Resurrector
from necromancer.resurrection.llm import LLMFix
from necromancer.ritual.planner import build_plan
from necromancer.workspace import Workspace


class FakeSandbox:
    def __init__(self, test_results: list[RunResult]) -> None:
        self.test_results = list(test_results)
        self.installs: list[list[str]] = []
        self.tests = 0
        self.cleaned = False

    async def install(self, job_id: str, repo: Path, reqs: list[str], **kw: Any) -> RunResult:
        self.installs.append(list(reqs))
        return RunResult(status=RunStatus.PASSED)

    async def test(self, job_id: str, repo: Path, targets: Any = None) -> RunResult:
        self.tests += 1
        return self.test_results.pop(0)

    async def cleanup(self, job_id: str) -> None:
        self.cleaned = True


class FakeLLM:
    def __init__(self) -> None:
        self.calls: list[str] = []

    async def fix_file(self, path: str, source: str, failure: str, notes: Any = None) -> LLMFix:
        self.calls.append(path)
        return LLMFix(path=path, new_source=source + "\n# repaired\n", explanation="Patched it.")


def make_cert(root: Path) -> DeathCertificate:
    scan = scan_repo(root)
    return DeathCertificate(
        vitals=VitalRecords(
            full_name="someone/deadrepo", url="https://github.com/someone/deadrepo"
        ),
        python_lines=40,
        python_files=len(scan.files),
        files=scan.files,
        markers=scan.markers,
        marker_counts=scan.counts,
        has_tests=True,
        dependencies=[
            Dependency(
                name="requests",
                spec="==2.2.1",
                pinned_version="2.2.1",
                source="requirements.txt",
                latest="2.32.3",
                status=DependencyStatus.OUTDATED,
            ),
            Dependency(
                name="nose",
                spec="==1.3.0",
                pinned_version="1.3.0",
                source="requirements.txt",
                status=DependencyStatus.DEAD,
                replacement="pytest",
            ),
        ],
    )


@pytest.fixture
def setup(tmp_path: Path, dead_repo: Path) -> tuple[Workspace, DeathCertificate]:
    ws = Workspace.for_job(tmp_path / "ws", "job1")
    ws.prepare()
    shutil.copytree(dead_repo, ws.before)
    return ws, make_cert(ws.before)


async def test_deterministic_pass_fixes_everything(
    setup: tuple[Workspace, DeathCertificate],
) -> None:
    ws, cert = setup
    plan = build_plan(cert, llm_enabled=True)
    sandbox = FakeSandbox([RunResult(status=RunStatus.PASSED)])
    events: list[tuple[str, dict]] = []

    async def emit(kind: str, data: dict) -> None:
        events.append((kind, data))

    result = await Resurrector(
        job_id="job1",
        workspace=ws,
        certificate=cert,
        plan=plan,
        sandbox=sandbox,  # type: ignore[arg-type]
        llm=FakeLLM(),
        emit=emit,  # type: ignore[arg-type]
    ).run()

    core = (ws.after / "deadrepo" / "core.py").read_text()
    ast.parse(core)
    assert "urllib.request" in core and ".items()" in core and "isinstance(word, str)" in core
    assert "from collections.abc import Mapping" in core
    assert "assertEqual(" in (ws.after / "tests" / "test_core.py").read_text()
    reqs = (ws.after / "requirements.txt").read_text()
    assert "requests==2.32.3" in reqs and "pytest" in reqs and "nose" not in reqs
    assert (ws.after / "tests" / "test_necromancer_smoke.py").exists()
    assert (ws.after / ".necromancer" / "plan" / "tasks.md").exists()
    # the pristine clone is untouched
    assert 'print "shouting", word' in (ws.before / "deadrepo" / "core.py").read_text()

    statuses = {t.kind: t.status for t in plan.tasks}
    assert statuses[TaskKind.VERIFY] is TaskStatus.DONE
    assert statuses[TaskKind.LLM] is TaskStatus.SKIPPED
    assert result.tests and result.tests.ok
    assert result.files_changed >= 4
    # pyupgrade already covers ABC imports and unittest aliases, so "api" may be empty here
    assert {d.source for d in result.diffs} >= {"py2to3", "pyupgrade", "deps", "smoke"}
    assert sandbox.cleaned
    assert any(k == "diff" for k, _ in events) and any(k == "task" for k, _ in events)


async def test_missing_dependency_is_added_and_reinstalled(
    setup: tuple[Workspace, DeathCertificate],
) -> None:
    ws, cert = setup
    plan = build_plan(cert, llm_enabled=False)
    sandbox = FakeSandbox(
        [
            RunResult(
                status=RunStatus.FAILED, tail="E   ModuleNotFoundError: No module named 'pytz'"
            ),
            RunResult(status=RunStatus.PASSED),
        ]
    )
    result = await Resurrector(
        job_id="job1",
        workspace=ws,
        certificate=cert,
        plan=plan,
        sandbox=sandbox,  # type: ignore[arg-type]
    ).run()
    assert "pytz" in (ws.after / "requirements.txt").read_text()
    assert len(sandbox.installs) == 2
    assert result.tests and result.tests.ok


async def test_llm_loop_repairs_blamed_file(setup: tuple[Workspace, DeathCertificate]) -> None:
    ws, cert = setup
    plan = build_plan(cert, llm_enabled=True)
    failing = RunResult(
        status=RunStatus.FAILED,
        tail="deadrepo/core.py:12: in shout\nE   NameError: boom",
    )
    sandbox = FakeSandbox([failing, RunResult(status=RunStatus.PASSED)])
    llm = FakeLLM()
    result = await Resurrector(
        job_id="job1",
        workspace=ws,
        certificate=cert,
        plan=plan,
        sandbox=sandbox,  # type: ignore[arg-type]
        llm=llm,  # type: ignore[arg-type]
    ).run()
    assert llm.calls == ["deadrepo/core.py"]
    assert result.iterations == 1
    assert "# repaired" in (ws.after / "deadrepo" / "core.py").read_text()
    statuses = {t.kind: t.status for t in plan.tasks}
    assert statuses[TaskKind.LLM] is TaskStatus.DONE
    assert statuses[TaskKind.VERIFY] is TaskStatus.DONE
    assert any(d.source == "llm" for d in result.diffs)


async def test_llm_loop_is_bounded(setup: tuple[Workspace, DeathCertificate]) -> None:
    ws, cert = setup
    plan = build_plan(cert, llm_enabled=True)
    failing = RunResult(status=RunStatus.FAILED, tail="deadrepo/core.py:12: in shout\nE   boom")
    sandbox = FakeSandbox([failing] * 10)
    result = await Resurrector(
        job_id="job1",
        workspace=ws,
        certificate=cert,
        plan=plan,
        sandbox=sandbox,  # type: ignore[arg-type]
        llm=FakeLLM(),
        max_iterations=3,  # type: ignore[arg-type]
    ).run()
    assert result.iterations == 2  # same file is tried at most twice
    assert {t.kind: t.status for t in plan.tasks}[TaskKind.LLM] is TaskStatus.FAILED


async def test_without_docker_verify_is_skipped(setup: tuple[Workspace, DeathCertificate]) -> None:
    ws, cert = setup
    plan = build_plan(cert, llm_enabled=False)

    class NoDocker(FakeSandbox):
        async def install(self, *a: Any, **kw: Any) -> RunResult:
            return RunResult(status=RunStatus.SKIPPED, reason="Docker is not available")

    result = await Resurrector(
        job_id="job1",
        workspace=ws,
        certificate=cert,
        plan=plan,
        sandbox=NoDocker([]),  # type: ignore[arg-type]
    ).run()
    assert {t.kind: t.status for t in plan.tasks}[TaskKind.VERIFY] is TaskStatus.SKIPPED
    assert result.install and result.install.status is RunStatus.SKIPPED


async def test_install_failure_with_passing_tests_is_reported(
    setup: tuple[Workspace, DeathCertificate],
) -> None:
    ws, cert = setup
    plan = build_plan(cert, llm_enabled=False)

    class BrokenSetup(FakeSandbox):
        async def install(self, *a: Any, **kw: Any) -> RunResult:
            return RunResult(status=RunStatus.FAILED, tail="FileNotFoundError: README.rst\n")

    result = await Resurrector(
        job_id="job1",
        workspace=ws,
        certificate=cert,
        plan=plan,  # type: ignore[arg-type]
        sandbox=BrokenSetup([RunResult(status=RunStatus.PASSED)]),  # type: ignore[arg-type]
    ).run()
    assert any("README.rst" in n and "manual look" in n for n in result.notes)


def test_meaningful_error_skips_pip_noise() -> None:
    from necromancer.resurrection.engine import meaningful_error

    tail = (
        '  File "setup.py", line 10, in <module>\n'
        "FileNotFoundError: [Errno 2] No such file or directory: 'README.rst'\n"
        "  [end of output]\n"
        "note: This error originates from a subprocess, and is likely not a problem with pip.\n"
        "error: subprocess-exited-with-error\n"
        "╰─> See above for output.\n"
    )
    assert meaningful_error(tail).startswith("FileNotFoundError: [Errno 2]")
    assert meaningful_error("just one line") == "just one line"
