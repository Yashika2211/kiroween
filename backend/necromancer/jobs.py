"""Job orchestration: summon → autopsy → (user) → ritual → resurrection → rise."""

from __future__ import annotations

import asyncio
import logging
import shutil
import time
import uuid
from typing import Any

from necromancer.autopsy.service import AutopsyService
from necromancer.config import Settings
from necromancer.db import JobStore
from necromancer.errors import InvalidJobState, JobNotFound, NecromancerError
from necromancer.events import EventBus
from necromancer.github.urls import RepoRef, parse_repo_url
from necromancer.models import ACTIVE_STATUSES, EventType, Job, JobStatus, utcnow
from necromancer.resurrection.engine import Resurrector
from necromancer.resurrection.llm import LLMFixer
from necromancer.rise.pr_body import pr_title, render_pr_body
from necromancer.rise.publisher import PublishError, publish
from necromancer.ritual.planner import build_plan
from necromancer.sandbox.runner import SandboxConfig, SandboxRunner
from necromancer.workspace import Workspace

log = logging.getLogger("necromancer.jobs")


class JobManager:
    def __init__(
        self,
        settings: Settings,
        store: JobStore,
        bus: EventBus | None = None,
        sandbox: SandboxRunner | None = None,
        max_concurrent: int = 2,
    ) -> None:
        self.settings = settings
        self.store = store
        self.bus = bus or EventBus()
        self.sandbox = sandbox or SandboxRunner(
            SandboxConfig(image=settings.sandbox_image, enabled=settings.sandbox_mode == "docker")
        )
        self._slots = asyncio.Semaphore(max_concurrent)
        self._tasks: dict[str, asyncio.Task[None]] = {}

    # ------------------------------------------------------------------ helpers

    def workspace(self, job_id: str) -> Workspace:
        return Workspace.for_job(self.settings.workspace_dir, job_id)

    def get(self, job_id: str) -> Job:
        job = self.store.get(job_id)
        if job is None:
            raise JobNotFound(f"No grave with id {job_id!r}.")
        return job

    async def _emit(self, job: Job, type_: EventType, data: dict[str, Any]) -> None:
        await self.bus.publish(job.id, type_, data)

    async def _set_status(self, job: Job, status: JobStatus) -> None:
        job.status = status
        job.updated_at = utcnow()
        self.store.save(job)
        await self._emit(job, "status", {"status": status.value})

    def _spawn(self, job_id: str, coro: Any) -> None:
        task = asyncio.create_task(coro, name=f"job-{job_id}")
        self._tasks[job_id] = task
        task.add_done_callback(lambda _t: self._tasks.pop(job_id, None))

    def is_running(self, job_id: str) -> bool:
        return job_id in self._tasks

    async def wait(self, job_id: str) -> None:
        task = self._tasks.get(job_id)
        if task:
            await task

    async def shutdown(self) -> None:
        for task in list(self._tasks.values()):
            task.cancel()
        await asyncio.gather(*self._tasks.values(), return_exceptions=True)

    # ------------------------------------------------------------------ summon / autopsy

    async def summon(self, url: str) -> Job:
        ref = parse_repo_url(url)
        job = Job(id=uuid.uuid4().hex[:12], repo=ref.full_name, url=ref.html_url)
        self.store.save(job)
        await self._emit(job, "status", {"status": job.status.value})
        self._spawn(job.id, self._run_autopsy(job, ref))
        return job

    async def _run_autopsy(self, job: Job, ref: RepoRef) -> None:
        async with self._slots:
            await self._set_status(job, JobStatus.AUTOPSY)

            async def emit(type_: str, data: dict[str, Any]) -> None:
                await self._emit(job, type_, data)  # type: ignore[arg-type]

            service = AutopsyService(
                sandbox=self.sandbox,
                github_token=self.settings.github_token,
                max_lines=self.settings.max_lines,
                max_repo_mb=self.settings.max_repo_mb,
            )
            try:
                cert = await service.run(job.id, ref, self.workspace(job.id), emit)
            except NecromancerError as exc:
                await self._fail(
                    job,
                    exc.message,
                    exc.code,
                    rejected=exc.code in {"repo_too_large", "not_a_python_repo", "clone_failed"},
                )
                return
            except Exception as exc:
                log.exception("autopsy crashed for %s", job.id)
                await self._fail(job, f"The autopsy failed unexpectedly: {exc}", "internal")
                return
            job.certificate = cert
            job.plan = build_plan(cert, llm_enabled=self.settings.llm_enabled)
            await self._emit(job, "certificate", cert.model_dump(mode="json"))
            await self._emit(job, "plan", job.plan.model_dump(mode="json"))
            await self._set_status(job, JobStatus.AUTOPSIED)
            self.bus.close(job.id)

    async def _fail(self, job: Job, message: str, code: str, *, rejected: bool = False) -> None:
        job.error = message
        job.error_code = code
        await self._emit(job, "error", {"message": message, "code": code})
        await self._set_status(job, JobStatus.REJECTED if rejected else JobStatus.FAILED)
        self.bus.close(job.id)

    # ------------------------------------------------------------------ resurrection / rise

    async def resurrect(self, job_id: str) -> Job:
        job = self.get(job_id)
        if job.status not in {JobStatus.AUTOPSIED, JobStatus.FAILED} or job.certificate is None:
            raise InvalidJobState(
                f"This grave is {job.status.value}; the ritual needs a finished autopsy."
            )
        if job_id in self._tasks:
            raise InvalidJobState("The ritual is already under way.")
        job.error = None
        job.error_code = None
        job.plan = build_plan(job.certificate, llm_enabled=self.settings.llm_enabled)
        self.bus.reopen(job.id)
        await self._set_status(job, JobStatus.RITUAL)
        self._spawn(job.id, self._run_resurrection(job))
        return job

    async def _run_resurrection(self, job: Job) -> None:
        assert job.certificate is not None and job.plan is not None
        async with self._slots:

            async def emit(type_: str, data: dict[str, Any]) -> None:
                await self._emit(job, type_, data)  # type: ignore[arg-type]

            await self._emit(job, "plan", job.plan.model_dump(mode="json"))
            await self._set_status(job, JobStatus.RESURRECTING)
            llm = None
            if self.settings.llm_enabled:
                llm = LLMFixer(self.settings.anthropic_api_key, self.settings.llm_model)
            ws = self.workspace(job.id)
            try:
                if not ws.before.exists():
                    raise InvalidJobState("The remains are gone (workspace cleaned); summon again.")
                result = await Resurrector(
                    job_id=job.id,
                    workspace=ws,
                    certificate=job.certificate,
                    plan=job.plan,
                    sandbox=self.sandbox,
                    llm=llm,
                    max_iterations=self.settings.max_fix_iterations,
                    emit=emit,
                ).run()
                job.result = result
                self.store.save(job)

                await self._set_status(job, JobStatus.RISING)
                ref = parse_repo_url(job.repo)
                title = pr_title(job.certificate, result)
                body = render_pr_body(job.certificate, job.plan, result)
                result.pr_body = body
                try:
                    published = await publish(
                        repo=ws.after,
                        upstream=ref,
                        default_branch=job.certificate.vitals.default_branch or "master",
                        job_id=job.id,
                        title=title,
                        body=body,
                        token=self.settings.github_token,
                    )
                    result.patch = published.patch
                    result.pr_url = published.pr_url
                    result.branch = published.branch
                    if not published.pr_url:
                        result.notes.append(
                            "No GITHUB_TOKEN configured: download the patch instead of a PR."
                        )
                except PublishError as exc:
                    result.notes.append(f"Could not open a pull request: {exc}")
                except Exception as exc:  # GitHub API failures shouldn't lose the work
                    result.notes.append(f"Could not open a pull request: {exc}")
                job.result = result
                await self._emit(job, "result", result.model_dump(mode="json", exclude={"patch"}))
                await self._set_status(job, JobStatus.RISEN)
            except NecromancerError as exc:
                await self._fail(job, exc.message, exc.code)
                return
            except Exception as exc:
                log.exception("resurrection crashed for %s", job.id)
                await self._fail(job, f"The ritual failed unexpectedly: {exc}", "internal")
                return
            self.bus.close(job.id)

    def delete(self, job_id: str) -> None:
        if job_id in self._tasks:
            raise InvalidJobState("Can't bury a job that is still running.")
        self.get(job_id)
        self.store.delete(job_id)
        self.workspace(job_id).destroy()

    def prune_workspaces(self, now: float | None = None) -> int:
        """Delete clones older than the TTL. Results and patches stay in the database."""
        root = self.settings.workspace_dir
        if self.settings.workspace_ttl_hours <= 0 or not root.is_dir():
            return 0
        cutoff = (
            now if now is not None else time.time()
        ) - self.settings.workspace_ttl_hours * 3600
        pruned = 0
        for path in root.iterdir():
            if not path.is_dir() or path.is_symlink() or self.is_running(path.name):
                continue
            if path.stat().st_mtime < cutoff:
                shutil.rmtree(path, ignore_errors=True)
                pruned += 1
        return pruned

    def recover(self) -> int:
        return self.store.mark_interrupted(ACTIVE_STATUSES)
