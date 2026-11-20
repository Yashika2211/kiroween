"""SQLite persistence for jobs (the graveyard). Whole jobs are stored as JSON documents."""

from __future__ import annotations

import sqlite3
import threading
from pathlib import Path

from necromancer.models import Job, JobStatus, JobSummary

SCHEMA = """
CREATE TABLE IF NOT EXISTS jobs (
    id          TEXT PRIMARY KEY,
    repo        TEXT NOT NULL,
    status      TEXT NOT NULL,
    created_at  TEXT NOT NULL,
    updated_at  TEXT NOT NULL,
    data        TEXT NOT NULL
);
CREATE INDEX IF NOT EXISTS jobs_created ON jobs (created_at DESC);
"""


class JobStore:
    def __init__(self, path: Path | str) -> None:
        if str(path) != ":memory:":
            Path(path).parent.mkdir(parents=True, exist_ok=True)
        self._conn = sqlite3.connect(str(path), check_same_thread=False)
        self._conn.execute("PRAGMA journal_mode=WAL")
        self._conn.executescript(SCHEMA)
        self._lock = threading.Lock()

    def close(self) -> None:
        self._conn.close()

    def save(self, job: Job) -> None:
        with self._lock, self._conn:
            self._conn.execute(
                "INSERT INTO jobs (id, repo, status, created_at, updated_at, data) "
                "VALUES (?, ?, ?, ?, ?, ?) "
                "ON CONFLICT(id) DO UPDATE SET status=excluded.status, "
                "updated_at=excluded.updated_at, data=excluded.data",
                (
                    job.id,
                    job.repo,
                    job.status.value,
                    job.created_at.isoformat(),
                    job.updated_at.isoformat(),
                    job.model_dump_json(),
                ),
            )

    def get(self, job_id: str) -> Job | None:
        with self._lock:
            row = self._conn.execute("SELECT data FROM jobs WHERE id = ?", (job_id,)).fetchone()
        return Job.model_validate_json(row[0]) if row else None

    def list(self, limit: int = 100) -> list[Job]:
        with self._lock:
            rows = self._conn.execute(
                "SELECT data FROM jobs ORDER BY created_at DESC LIMIT ?", (limit,)
            ).fetchall()
        return [Job.model_validate_json(r[0]) for r in rows]

    def delete(self, job_id: str) -> bool:
        with self._lock, self._conn:
            cur = self._conn.execute("DELETE FROM jobs WHERE id = ?", (job_id,))
        return cur.rowcount > 0

    def mark_interrupted(self, active: set[JobStatus]) -> int:
        """Jobs that were running when the server stopped can't resume; fail them."""
        count = 0
        for job in self.list(limit=10_000):
            if job.status in active:
                job.status = JobStatus.FAILED
                job.error = "Interrupted: the server restarted while this job was running."
                job.error_code = "interrupted"
                self.save(job)
                count += 1
        return count


def summarize(job: Job) -> JobSummary:
    cert = job.certificate
    vitals = cert.vitals if cert else None
    return JobSummary(
        id=job.id,
        repo=job.repo,
        status=job.status,
        created_at=job.created_at,
        born=vitals.created_at.year if vitals and vitals.created_at else None,
        died=vitals.last_commit_at.year if vitals and vitals.last_commit_at else None,
        cause_of_death=cert.cause_of_death if cert else job.error,
        decay_score=cert.decay_score if cert else None,
        pr_url=job.result.pr_url if job.result else None,
        tests_passed=(job.result.tests.ok if job.result and job.result.tests else None),
    )
