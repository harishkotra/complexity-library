from __future__ import annotations

import time
from collections import defaultdict, deque


class SlidingWindowRateLimiter:
    """Process-local limiter for development; production can replace this boundary with Redis."""

    def __init__(self) -> None:
        self._events: dict[str, deque[float]] = defaultdict(deque)

    def check(self, key: str, limit: int, window_seconds: int, now: float | None = None) -> tuple[bool, int]:
        current = time.time() if now is None else now
        events = self._events[key]
        while events and events[0] <= current - window_seconds:
            events.popleft()
        if len(events) >= limit:
            return False, max(1, int(window_seconds - (current - events[0])))
        events.append(current)
        return True, 0
