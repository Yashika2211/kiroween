from collections.abc import AsyncIterator
from dataclasses import replace
from pathlib import Path
from typing import Any

import httpx
import pytest

from necromancer import jobs as jobs_mod
from necromancer.api.app import create_app
from necromancer.config import get_settings
from necromancer.db import JobStore
from necromancer.errors import RepoTooLarge
from necromancer.jobs import JobManager
from necromancer.models import ResurrectionResult, RunResult, RunStatus, TaskStatus
from necromancer.rise.publisher import Published
from necromancer.sandbox.runner import SandboxConfig, SandboxRunner
from tests.factories import certificate


@pytest.fixture
async def client(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> AsyncIterator[tuple[httpx.AsyncClient, JobManager]]:
    settings = replace(
        get_settings(),
        db_path=tmp_path / "db.sqlite3",
        workspace_dir=tmp_path / "ws",
        github_token=None,
        anthropic_api_key=None,
    )

    async def fake_autopsy(self: Any, job_id: str, ref: Any, ws: Any, emit: Any) -> Any:
        await emit("step", {"key": "exhume", "state": "done"})
        if ref.name == "huge":
            raise RepoTooLarge("too big")
        ws.prepare()
        ws.before.mkdir()
        return certificate()

    async def fake_resurrect(self: Any) -> ResurrectionResult:
        await self.emit("log", {"message": "rising"})
        return ResurrectionResult(tests=RunResult(status=RunStatus.PASSED, tail="1 passed"))

    async def fake_publish(**kw: Any) -> Published:
        return Published(pr_url=None, branch="b", fork=None, patch="--- a\n+++ b\n")

    monkeypatch.setattr(jobs_mod.AutopsyService, "run", fake_autopsy)
    monkeypatch.setattr(jobs_mod.Resurrector, "run", fake_resurrect)
    monkeypatch.setattr(jobs_mod, "publish", fake_publish)

    manager = JobManager(
        settings, JobStore(settings.db_path), sandbox=SandboxRunner(SandboxConfig(enabled=False))
    )
    app = create_app(settings, manager)
    async with app.router.lifespan_context(app):
        transport = httpx.ASGITransport(app=app)
        async with httpx.AsyncClient(transport=transport, base_url="http://test") as c:
            yield c, manager


async def test_health(client: tuple[httpx.AsyncClient, JobManager]) -> None:
    c, _ = client
    body = (await c.get("/api/health")).json()
    assert body["ok"] is True and body["docker"] is False and body["llm"] is False


async def test_summon_validates_url(client: tuple[httpx.AsyncClient, JobManager]) -> None:
    c, _ = client
    r = await c.post("/api/summon", json={"url": "https://gitlab.com/a/b"})
    assert r.status_code == 422 and r.json()["code"] == "invalid_repo_url"


async def test_full_lifecycle(client: tuple[httpx.AsyncClient, JobManager]) -> None:
    c, manager = client
    r = await c.post("/api/summon", json={"url": "https://github.com/someone/deadrepo"})
    assert r.status_code == 202
    job_id = r.json()["id"]
    await manager.wait(job_id)

    job = (await c.get(f"/api/jobs/{job_id}")).json()
    assert job["status"] == "autopsied"
    assert job["certificate"]["decay_score"] == 78
    assert job["plan"]["tasks"]

    graves = (await c.get("/api/jobs")).json()
    assert graves[0]["repo"] == "someone/deadrepo" and graves[0]["born"] == 2011

    r = await c.post(f"/api/jobs/{job_id}/resurrect")
    assert r.status_code == 202
    await manager.wait(job_id)
    job = (await c.get(f"/api/jobs/{job_id}")).json()
    assert job["status"] == "risen"
    assert job["result"]["patch"] is None  # not inlined
    patch = await c.get(f"/api/jobs/{job_id}/patch")
    assert patch.status_code == 200 and patch.text.startswith("--- a")

    # the event stream replays everything that happened, then ends
    async with c.stream("GET", f"/api/jobs/{job_id}/events") as stream:
        text = "".join([chunk async for chunk in stream.aiter_text()])
    for event in ("status", "step", "certificate", "plan", "log", "result", "end"):
        assert f"event: {event}" in text

    r = await c.post(f"/api/jobs/{job_id}/resurrect")
    assert r.status_code == 409

    assert (await c.delete(f"/api/jobs/{job_id}")).status_code == 204
    assert (await c.get(f"/api/jobs/{job_id}")).status_code == 404


async def test_rejected_repo(client: tuple[httpx.AsyncClient, JobManager]) -> None:
    c, manager = client
    job_id = (await c.post("/api/summon", json={"url": "someone/huge"})).json()["id"]
    await manager.wait(job_id)
    job = (await c.get(f"/api/jobs/{job_id}")).json()
    assert job["status"] == "rejected" and job["error_code"] == "repo_too_large"


async def test_summon_is_rate_limited(tmp_path: Path) -> None:
    settings = replace(
        get_settings(),
        db_path=tmp_path / "db.sqlite3",
        workspace_dir=tmp_path / "ws",
        rate_limit_per_hour=1,
    )
    manager = JobManager(
        settings, JobStore(settings.db_path), sandbox=SandboxRunner(SandboxConfig(enabled=False))
    )
    app = create_app(settings, manager)
    async with (
        app.router.lifespan_context(app),
        httpx.AsyncClient(transport=httpx.ASGITransport(app=app), base_url="http://t") as c,
    ):
        bad = {"url": "not a url"}  # validation happens after the limiter, so no job starts
        assert (await c.post("/api/summon", json=bad)).status_code == 422
        r = await c.post("/api/summon", json=bad)
        assert r.status_code == 429 and r.json()["code"] == "rate_limited"


async def test_finished_job_after_restart_gets_snapshot_then_end(
    client: tuple[httpx.AsyncClient, JobManager],
) -> None:
    c, manager = client
    job_id = (await c.post("/api/summon", json={"url": "someone/deadrepo"})).json()["id"]
    await manager.wait(job_id)
    manager.bus = type(manager.bus)()  # simulate a server restart: no in-memory history
    async with c.stream("GET", f"/api/jobs/{job_id}/events") as stream:
        text = "".join([chunk async for chunk in stream.aiter_text()])
    assert "event: snapshot" in text and "event: end" in text


async def test_job_snapshot_carries_event_seq_and_stream_resumes_after_it(
    client: tuple[httpx.AsyncClient, JobManager],
) -> None:
    c, manager = client
    job_id = (await c.post("/api/summon", json={"url": "someone/deadrepo"})).json()["id"]
    await manager.wait(job_id)
    r = await c.get(f"/api/jobs/{job_id}")
    seq = int(r.headers["x-event-seq"])
    assert seq == manager.bus.last_seq(job_id) > 3
    async with c.stream("GET", f"/api/jobs/{job_id}/events?after={seq - 1}") as stream:
        text = "".join([chunk async for chunk in stream.aiter_text()])
    assert text.count("id: ") == 1 and f"id: {seq}" in text


async def test_task_progress_is_persisted_mid_ritual(
    client: tuple[httpx.AsyncClient, JobManager], monkeypatch: pytest.MonkeyPatch
) -> None:
    c, manager = client
    seen: list[str] = []

    async def slow_resurrect(self: Any) -> ResurrectionResult:
        task = self.plan.tasks[0]
        task.status = TaskStatus.DONE
        await self.emit("task", task.model_dump())
        stored = manager.store.get(self.job_id)
        assert stored is not None and stored.plan is not None
        seen.append(stored.plan.tasks[0].status)
        return ResurrectionResult(tests=RunResult(status=RunStatus.PASSED))

    monkeypatch.setattr(jobs_mod.Resurrector, "run", slow_resurrect)
    job_id = (await c.post("/api/summon", json={"url": "someone/deadrepo"})).json()["id"]
    await manager.wait(job_id)
    await c.post(f"/api/jobs/{job_id}/resurrect")
    await manager.wait(job_id)
    assert seen == ["done"]
