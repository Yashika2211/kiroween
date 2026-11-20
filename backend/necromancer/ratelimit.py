"""Tiny in-memory sliding-window rate limiter for the endpoints that start sandbox work."""

from __future__ import annotations

import time
from collections import defaultdict, deque
from collections.abc import Callable


class RateLimiter:
    def __init__(
        self, limit: int, window_s: float, clock: Callable[[], float] = time.monotonic
    ) -> None:
        self.limit = limit
        self.window_s = window_s
        self._clock = clock
        self._hits: dict[str, deque[float]] = defaultdict(deque)

    def check(self, key: str) -> float | None:
        """Record a hit for `key`. Returns None if allowed, else seconds until a slot frees."""
        if self.limit <= 0:
            return None
        now = self._clock()
        hits = self._hits[key]
        while hits and now - hits[0] >= self.window_s:
            hits.popleft()
        if len(hits) >= self.limit:
            return max(0.0, self.window_s - (now - hits[0]))
        hits.append(now)
        return None
