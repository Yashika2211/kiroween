"""Pydantic models shared across the pipeline and the HTTP API.

These are the contract with the frontend (`frontend/lib/types.ts`); keep both in sync.
"""

from __future__ import annotations

from datetime import UTC, datetime
from enum import StrEnum
from typing import Any, Literal

from pydantic import BaseModel, Field


def utcnow() -> datetime:
    return datetime.now(UTC)


# --------------------------------------------------------------------------- autopsy


class MarkerCategory(StrEnum):
    SYNTAX = "syntax"
    BUILTIN = "builtin"
    STDLIB = "stdlib"
    API = "api"


class Marker(BaseModel):
    """A single sign that a file was written for an older Python."""

    file: str
    line: int
    kind: str
    category: MarkerCategory
    excerpt: str
    hint: str = ""


class FileHealth(BaseModel):
    path: str
    lines: int
    parses: bool
    error: str | None = None


class DependencyStatus(StrEnum):
    OK = "ok"
    OUTDATED = "outdated"
    UNPINNED = "unpinned"
    MISSING = "missing"
    DEAD = "dead"
    UNKNOWN = "unknown"


class Dependency(BaseModel):
    name: str
    spec: str = ""
    pinned_version: str | None = None
    source: str
    latest: str | None = None
    status: DependencyStatus = DependencyStatus.UNKNOWN
    replacement: str | None = None
    note: str = ""


class Severity(StrEnum):
    LOW = "low"
    MODERATE = "moderate"
    HIGH = "high"
    CRITICAL = "critical"
    UNKNOWN = "unknown"


class Vulnerability(BaseModel):
    id: str
    package: str
    version: str | None = None
    aliases: list[str] = Field(default_factory=list)
    summary: str = ""
    severity: Severity = Severity.UNKNOWN
    fixed: str | None = None
    url: str = ""


class RunStatus(StrEnum):
    PASSED = "passed"
    FAILED = "failed"
    TIMEOUT = "timeout"
    ERROR = "error"
    SKIPPED = "skipped"


class RunResult(BaseModel):
    status: RunStatus
    exit_code: int | None = None
    duration_s: float = 0.0
    command: str = ""
    tail: str = ""
    reason: str = ""

    @property
    def ok(self) -> bool:
        return self.status == RunStatus.PASSED


class VitalRecords(BaseModel):
    full_name: str
    url: str
    description: str | None = None
    created_at: datetime | None = None
    last_commit_at: datetime | None = None
    pushed_at: datetime | None = None
    stars: int | None = None
    forks: int | None = None
    open_issues: int | None = None
    archived: bool | None = None
    default_branch: str | None = None
    license: str | None = None
    api_available: bool = True


class DecayFactor(BaseModel):
    key: str
    label: str
    points: float
    max_points: float
    detail: str


class DeathCertificate(BaseModel):
    vitals: VitalRecords
    python_lines: int
    python_files: int
    files: list[FileHealth] = Field(default_factory=list)
    markers: list[Marker] = Field(default_factory=list)
    marker_counts: dict[str, int] = Field(default_factory=dict)
    has_tests: bool = False
    dependencies: list[Dependency] = Field(default_factory=list)
    vulnerabilities: list[Vulnerability] = Field(default_factory=list)
    probe: RunResult | None = None
    decay_score: int = 0
    decay_label: str = ""
    decay_breakdown: list[DecayFactor] = Field(default_factory=list)
    cause_of_death: str = ""
    contributing_factors: list[str] = Field(default_factory=list)
    warnings: list[str] = Field(default_factory=list)
    generated_at: datetime = Field(default_factory=utcnow)
    duration_s: float = 0.0

    @property
    def unparseable_files(self) -> list[FileHealth]:
        return [f for f in self.files if not f.parses]


# --------------------------------------------------------------------------- ritual


class TaskKind(StrEnum):
    REWRITE = "rewrite"
    API = "api"
    DEPS = "deps"
    VULNS = "vulns"
    TESTS = "tests"
    VERIFY = "verify"
    LLM = "llm"


class TaskStatus(StrEnum):
    PENDING = "pending"
    RUNNING = "running"
    DONE = "done"
    FAILED = "failed"
    SKIPPED = "skipped"


class PlanTask(BaseModel):
    id: str
    title: str
    kind: TaskKind
    files: list[str] = Field(default_factory=list)
    requirement_ids: list[str] = Field(default_factory=list)
    status: TaskStatus = TaskStatus.PENDING
    note: str = ""


class ResurrectionPlan(BaseModel):
    requirements_md: str
    design_md: str
    tasks_md: str
    tasks: list[PlanTask]


# --------------------------------------------------------------------------- resurrection


FixSource = Literal["py2to3", "pyupgrade", "api", "deps", "vulns", "smoke", "llm"]


class FileDiff(BaseModel):
    path: str
    source: FixSource
    diff: str
    added: int = 0
    removed: int = 0


class ResurrectionResult(BaseModel):
    tests: RunResult | None = None
    install: RunResult | None = None
    iterations: int = 0
    diffs: list[FileDiff] = Field(default_factory=list)
    files_changed: int = 0
    generated_tests: list[str] = Field(default_factory=list)
    pr_url: str | None = None
    branch: str | None = None
    patch: str | None = None
    pr_body: str | None = None
    notes: list[str] = Field(default_factory=list)


# --------------------------------------------------------------------------- jobs


class JobStatus(StrEnum):
    QUEUED = "queued"
    AUTOPSY = "autopsy"
    AUTOPSIED = "autopsied"
    RITUAL = "ritual"
    RESURRECTING = "resurrecting"
    RISING = "rising"
    RISEN = "risen"
    FAILED = "failed"
    REJECTED = "rejected"


ACTIVE_STATUSES = {
    JobStatus.QUEUED,
    JobStatus.AUTOPSY,
    JobStatus.RITUAL,
    JobStatus.RESURRECTING,
    JobStatus.RISING,
}


class Job(BaseModel):
    id: str
    repo: str
    url: str
    status: JobStatus = JobStatus.QUEUED
    created_at: datetime = Field(default_factory=utcnow)
    updated_at: datetime = Field(default_factory=utcnow)
    certificate: DeathCertificate | None = None
    plan: ResurrectionPlan | None = None
    result: ResurrectionResult | None = None
    error: str | None = None
    error_code: str | None = None


class JobSummary(BaseModel):
    """Small projection used by the graveyard grid."""

    id: str
    repo: str
    status: JobStatus
    created_at: datetime
    born: int | None = None
    died: int | None = None
    cause_of_death: str | None = None
    decay_score: int | None = None
    pr_url: str | None = None
    tests_passed: bool | None = None


EventType = Literal[
    "status", "step", "log", "certificate", "plan", "task", "diff", "test", "result", "error"
]


class JobEvent(BaseModel):
    seq: int
    job_id: str
    type: EventType
    data: dict[str, Any] = Field(default_factory=dict)
    ts: datetime = Field(default_factory=utcnow)
