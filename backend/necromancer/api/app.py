"""HTTP API: REST for jobs plus a Server-Sent Events stream per job."""

from __future__ import annotations

import json
from collections.abc import AsyncIterator
from contextlib import asynccontextmanager

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse, PlainTextResponse
from pydantic import BaseModel, Field
from sse_starlette.sse import EventSourceResponse

from necromancer import __version__
from necromancer.config import Settings, get_settings
from necromancer.db import JobStore, summarize
from necromancer.errors import (
    InvalidJobState,
    InvalidRepoURL,
    JobNotFound,
    NecromancerError,
    RateLimited,
)
from necromancer.jobs import JobManager
from necromancer.models import Job, JobSummary
from necromancer.ratelimit import RateLimiter

STATUS_FOR = {
    InvalidRepoURL: 422,
    JobNotFound: 404,
    InvalidJobState: 409,
    RateLimited: 429,
}


class SummonRequest(BaseModel):
    url: str = Field(min_length=1, max_length=300)


class Health(BaseModel):
    ok: bool
    version: str
    docker: bool
    llm: bool
    github: bool


def create_app(settings: Settings | None = None, manager: JobManager | None = None) -> FastAPI:
    cfg = settings or get_settings()

    @asynccontextmanager
    async def lifespan(app: FastAPI) -> AsyncIterator[None]:
        mgr = manager or JobManager(cfg, JobStore(cfg.db_path))
        mgr.recover()
        mgr.prune_workspaces()
        app.state.manager = mgr
        yield
        await mgr.shutdown()

    app = FastAPI(
        title="Necromancer",
        version=__version__,
        description="Resurrects abandoned open-source Python repositories.",
        lifespan=lifespan,
    )
    app.add_middleware(
        CORSMiddleware,
        allow_origins=cfg.cors_origins,
        allow_methods=["GET", "POST", "DELETE"],
        allow_headers=["Content-Type", "Last-Event-ID"],
    )

    limiter = RateLimiter(cfg.rate_limit_per_hour, 3600)

    def throttle(request: Request) -> None:
        """Summoning and resurrecting start Docker work, so they are rate limited per client."""
        client = request.client.host if request.client else "unknown"
        wait = limiter.check(client)
        if wait is not None:
            raise RateLimited(
                f"Too many summonings from this address. Try again in {int(wait // 60) + 1} min."
            )

    def mgr(request: Request) -> JobManager:
        return request.app.state.manager  # type: ignore[no-any-return]

    @app.exception_handler(NecromancerError)
    async def handle_error(_request: Request, exc: NecromancerError) -> JSONResponse:
        status = next((s for cls, s in STATUS_FOR.items() if isinstance(exc, cls)), 400)
        return JSONResponse({"code": exc.code, "message": exc.message}, status_code=status)

    @app.get("/api/health", response_model=Health)
    async def health(request: Request) -> Health:
        m = mgr(request)
        return Health(
            ok=True,
            version=__version__,
            docker=await m.sandbox.available(),
            llm=cfg.llm_enabled,
            github=cfg.can_open_prs,
        )

    @app.post("/api/summon", response_model=Job, status_code=202)
    async def summon(body: SummonRequest, request: Request) -> Job:
        throttle(request)
        return await mgr(request).summon(body.url)

    @app.get("/api/jobs", response_model=list[JobSummary])
    async def list_jobs(request: Request) -> list[JobSummary]:
        return [summarize(j) for j in mgr(request).store.list()]

    @app.get("/api/jobs/{job_id}", response_model=Job)
    async def get_job(job_id: str, request: Request) -> Job:
        job = mgr(request).get(job_id)
        if job.result and job.result.patch:
            job.result.patch = None  # served separately; can be large
        return job

    @app.post("/api/jobs/{job_id}/resurrect", response_model=Job, status_code=202)
    async def resurrect(job_id: str, request: Request) -> Job:
        throttle(request)
        return await mgr(request).resurrect(job_id)

    @app.delete("/api/jobs/{job_id}", status_code=204)
    async def delete_job(job_id: str, request: Request) -> None:
        mgr(request).delete(job_id)

    @app.get("/api/jobs/{job_id}/patch", response_class=PlainTextResponse)
    async def patch(job_id: str, request: Request) -> PlainTextResponse:
        job = mgr(request).get(job_id)
        if not job.result or not job.result.patch:
            raise JobNotFound("No patch for this job yet.")
        name = job.repo.replace("/", "-")
        return PlainTextResponse(
            job.result.patch,
            media_type="text/x-diff",
            headers={"Content-Disposition": f'attachment; filename="{name}-resurrected.patch"'},
        )

    @app.get("/api/jobs/{job_id}/events")
    async def events(job_id: str, request: Request) -> EventSourceResponse:
        m = mgr(request)
        job = m.get(job_id)
        last_id = request.headers.get("last-event-id", "0")
        after = int(last_id) if last_id.isdigit() else 0

        async def stream() -> AsyncIterator[dict[str, str]]:
            # A job from before a restart has no live history; send its final state.
            if not m.bus.history(job_id) and not m.is_running(job_id):
                yield {
                    "event": "snapshot",
                    "data": job.model_dump_json(exclude={"result": {"patch"}}),
                }
                return
            async for event in m.bus.subscribe(job_id, after):
                if await request.is_disconnected():
                    return
                yield {
                    "id": str(event.seq),
                    "event": event.type,
                    "data": json.dumps(event.data, default=str),
                }
            yield {"event": "end", "data": "{}"}

        return EventSourceResponse(stream(), ping=15)

    return app


app = create_app()
