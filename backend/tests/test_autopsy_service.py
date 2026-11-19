import shutil
from pathlib import Path

import pytest
import respx

from necromancer.autopsy import service as service_mod
from necromancer.autopsy.osv import OSV_API
from necromancer.autopsy.pypi import PYPI
from necromancer.autopsy.service import AutopsyService, detect_tests, requirement_files
from necromancer.errors import RepoTooLarge
from necromancer.github.client import API
from necromancer.github.urls import RepoRef
from necromancer.models import DependencyStatus, RunStatus
from necromancer.sandbox.runner import SandboxConfig, SandboxRunner
from necromancer.workspace import Workspace

REF = RepoRef("someone", "deadrepo")


@pytest.fixture
def fake_clone(dead_repo: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    async def clone(ref: RepoRef, dest: Path, **kwargs: object) -> Path:
        shutil.copytree(dead_repo, dest)
        return dest

    async def no_date(_: Path) -> None:
        return None

    monkeypatch.setattr(service_mod, "clone_repo", clone)
    monkeypatch.setattr(service_mod, "last_commit_date", no_date)
    monkeypatch.setattr(service_mod, "first_commit_date", no_date)


def mock_network() -> None:
    respx.get(f"{API}/repos/someone/deadrepo").respond(
        json={
            "full_name": "someone/deadrepo",
            "created_at": "2011-01-01T00:00:00Z",
            "pushed_at": "2013-03-12T00:00:00Z",
            "archived": True,
            "default_branch": "master",
        }
    )
    respx.get(f"{API}/repos/someone/deadrepo/commits").respond(
        json=[{"commit": {"committer": {"date": "2013-03-12T00:00:00Z"}}}]
    )
    respx.get(f"{PYPI}/requests/json").respond(
        json={"info": {"version": "2.32.3"}, "releases": {"2.32.3": [{"requires_python": ">=3.8"}]}}
    )
    respx.get(f"{PYPI}/nose/json").respond(
        json={"info": {"version": "1.3.7"}, "releases": {"1.3.7": [{}]}}
    )
    respx.post(f"{OSV_API}/querybatch").respond(
        json={"results": [{"vulns": [{"id": "GHSA-x"}]}, {}]}
    )
    respx.get(f"{OSV_API}/vulns/GHSA-x").respond(
        json={
            "id": "GHSA-x",
            "summary": "Requests leaks credentials",
            "database_specific": {"severity": "HIGH"},
            "affected": [
                {"package": {"name": "requests"}, "ranges": [{"events": [{"fixed": "2.3.0"}]}]}
            ],
        }
    )


@respx.mock
async def test_full_autopsy_on_fixture(tmp_path: Path, fake_clone: None) -> None:
    mock_network()
    events: list[tuple[str, dict]] = []

    async def emit(kind: str, data: dict) -> None:
        events.append((kind, data))

    svc = AutopsyService(sandbox=SandboxRunner(SandboxConfig(enabled=False)))
    ws = Workspace.for_job(tmp_path / "ws", "job1")
    cert = await svc.run("job1", REF, ws, emit)

    assert cert.vitals.archived is True
    assert cert.python_files == 4
    assert cert.has_tests is True
    assert [f.path for f in cert.unparseable_files] == ["deadrepo/core.py"]
    for kind in (
        "removed_module",
        "print_statement",
        "dict_iteritems",
        "basestring",
        "except_comma",
    ):
        assert kind in cert.marker_counts
    deps = {d.name: d for d in cert.dependencies}
    assert deps["requests"].status is DependencyStatus.OUTDATED
    assert deps["nose"].status is DependencyStatus.DEAD
    assert cert.vulnerabilities[0].fixed == "2.3.0"
    assert cert.probe and cert.probe.status is RunStatus.SKIPPED
    assert cert.cause_of_death.startswith("Acute Python 2 syndrome")
    assert 50 <= cert.decay_score <= 100
    assert any("probe skipped" in w for w in cert.warnings)

    done_steps = [d["key"] for k, d in events if k == "step" and d["state"] == "done"]
    assert set(done_steps) == {key for key, _ in service_mod.STEPS}
    assert done_steps[0] == "exhume" and done_steps[-1] == "verdict"


@respx.mock
async def test_autopsy_rejects_large_repo(tmp_path: Path, fake_clone: None) -> None:
    svc = AutopsyService(sandbox=SandboxRunner(SandboxConfig(enabled=False)), max_lines=10)
    with pytest.raises(RepoTooLarge):
        await svc.run("job2", REF, Workspace.for_job(tmp_path, "job2"))


@respx.mock
async def test_autopsy_survives_github_outage(tmp_path: Path, fake_clone: None) -> None:
    mock_network()
    respx.get(f"{API}/repos/someone/deadrepo").respond(
        status_code=403, json={"message": "rate limit"}
    )
    svc = AutopsyService(sandbox=SandboxRunner(SandboxConfig(enabled=False)))
    cert = await svc.run("job3", REF, Workspace.for_job(tmp_path, "job3"))
    assert cert.vitals.api_available is False
    assert any("GitHub API unavailable" in w for w in cert.warnings)


def test_helpers(dead_repo: Path) -> None:
    assert requirement_files(dead_repo) == ["requirements.txt"]
    assert detect_tests(dead_repo) is True
