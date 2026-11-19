from datetime import UTC, datetime, timedelta

from necromancer.db import JobStore, summarize
from necromancer.models import ACTIVE_STATUSES, Job, JobStatus
from tests.factories import certificate


def test_save_get_list_delete() -> None:
    store = JobStore(":memory:")
    older = Job(id="a", repo="x/a", url="u", created_at=datetime.now(UTC) - timedelta(hours=1))
    newer = Job(id="b", repo="x/b", url="u", certificate=certificate())
    store.save(older)
    store.save(newer)
    newer.status = JobStatus.RISEN
    store.save(newer)
    got = store.get("b")
    assert got is not None and got.status is JobStatus.RISEN
    assert got.certificate is not None and got.certificate.decay_score == 78
    assert [j.id for j in store.list()] == ["b", "a"]
    assert store.delete("a") and store.get("a") is None
    assert store.get("missing") is None


def test_mark_interrupted() -> None:
    store = JobStore(":memory:")
    store.save(Job(id="run", repo="x/y", url="u", status=JobStatus.RESURRECTING))
    store.save(Job(id="done", repo="x/y", url="u", status=JobStatus.RISEN))
    assert store.mark_interrupted(ACTIVE_STATUSES) == 1
    job = store.get("run")
    assert job is not None and job.status is JobStatus.FAILED and job.error_code == "interrupted"


def test_summary_has_tombstone_fields() -> None:
    s = summarize(Job(id="b", repo="someone/deadrepo", url="u", certificate=certificate()))
    assert (s.born, s.died, s.decay_score) == (2011, 2013, 78)
    assert s.cause_of_death and s.cause_of_death.startswith("Acute")
