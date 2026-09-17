"""Sliding-window rate limiter (in-memory; swap for Redis in production via same interface)."""

from __future__ import annotations

import threading
import time
from collections import defaultdict, deque
from typing import Deque, Dict, Tuple

from app.core.config import get_settings
from app.core.errors import RateLimitedError

_lock = threading.Lock()
_hits: Dict[Tuple[str, str], Deque[float]] = defaultdict(deque)

_SCOPE_LIMIT_ATTR = {
    "ai": "RATE_LIMIT_AI_PER_MIN",
    "auth": "RATE_LIMIT_AUTH_PER_MIN",
    "search": "RATE_LIMIT_SEARCH_PER_MIN",
}


def enforce(scope: str, identity: str) -> None:
    attr = _SCOPE_LIMIT_ATTR.get(scope)
    limit = getattr(get_settings(), attr) if attr else 120
    key = (scope, identity)
    now = time.monotonic()
    with _lock:
        window = _hits[key]
        while window and now - window[0] > 60.0:
            window.popleft()
        if len(window) >= limit:
            retry_after = int(60 - (now - window[0])) + 1
            raise RateLimitedError(
                "Too many requests. Please wait a moment and try again.",
                details={"scope": scope, "retry_after_seconds": retry_after},
            )
        window.append(now)
