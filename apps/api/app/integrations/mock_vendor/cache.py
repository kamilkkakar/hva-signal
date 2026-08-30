"""In-process fingerprint cache for the mock lifecycle.

LIVE-H may replace this. Writes happen after normalization and before consume
so AFTER_CACHE_BEFORE_CONSUME is observable.
"""

from __future__ import annotations

from threading import Lock
from typing import Any


class InMemoryMockResultCache:
    """Fingerprint → normalized snapshot dump. Process-local only."""

    def __init__(self) -> None:
        self._lock = Lock()
        self._items: dict[str, dict[str, Any]] = {}

    def get(self, request_fingerprint: str) -> dict[str, Any] | None:
        with self._lock:
            item = self._items.get(request_fingerprint)
            return None if item is None else dict(item)

    def put(self, request_fingerprint: str, snapshot: dict[str, Any]) -> None:
        with self._lock:
            self._items[request_fingerprint] = dict(snapshot)

    def contains(self, request_fingerprint: str) -> bool:
        with self._lock:
            return request_fingerprint in self._items
