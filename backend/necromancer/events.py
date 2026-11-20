"""In-memory event bus: per-job history plus live subscribers (for Server-Sent Events)."""

from __future__ import annotations

import asyncio
from collections import defaultdict
from collections.abc import AsyncIterator
from typing import Any

from necromancer.models import EventType, JobEvent

MAX_HISTORY = 2000
_DONE = object()


class EventBus:
    def __init__(self) -> None:
        self._history: dict[str, list[JobEvent]] = defaultdict(list)
        self._subscribers: dict[str, set[asyncio.Queue[object]]] = defaultdict(set)
        self._seq: dict[str, int] = defaultdict(int)
        self._closed: set[str] = set()

    async def publish(self, job_id: str, type_: EventType, data: dict[str, Any]) -> JobEvent:
        self._seq[job_id] += 1
        event = JobEvent(seq=self._seq[job_id], job_id=job_id, type=type_, data=data)
        history = self._history[job_id]
        history.append(event)
        if len(history) > MAX_HISTORY:
            del history[: len(history) - MAX_HISTORY]
        for queue in list(self._subscribers[job_id]):
            queue.put_nowait(event)
        return event

    def last_seq(self, job_id: str) -> int:
        return self._seq.get(job_id, 0)

    def history(self, job_id: str, after: int = 0) -> list[JobEvent]:
        return [e for e in self._history.get(job_id, []) if e.seq > after]

    def close(self, job_id: str) -> None:
        """Signal subscribers that no more events will come for this stage."""
        self._closed.add(job_id)
        for queue in list(self._subscribers[job_id]):
            queue.put_nowait(_DONE)

    def reopen(self, job_id: str) -> None:
        self._closed.discard(job_id)

    def is_closed(self, job_id: str) -> bool:
        return job_id in self._closed

    async def subscribe(self, job_id: str, after: int = 0) -> AsyncIterator[JobEvent]:
        """Replay history after `after`, then stream live events until the job closes."""
        queue: asyncio.Queue[object] = asyncio.Queue()
        self._subscribers[job_id].add(queue)
        try:
            last = after
            for event in self.history(job_id, after):
                last = event.seq
                yield event
            if job_id in self._closed:
                return
            while True:
                item = await queue.get()
                if item is _DONE:
                    return
                assert isinstance(item, JobEvent)
                if item.seq > last:
                    last = item.seq
                    yield item
        finally:
            self._subscribers[job_id].discard(queue)
