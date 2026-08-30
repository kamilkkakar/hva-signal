"""Anonymous rate-limit seam. Not identity. Hard demo budget remains the backstop.

IP is not treated as a user account. Default implementation is a no-op.
"""

from __future__ import annotations

from threading import Lock
from typing import Protocol


class AnonymousRateLimit(Protocol):
    def allow_live_attempt(self, fingerprint: str) -> bool: ...


class NoOpAnonymousRateLimit:
    """Hard budget / reservation is the financial control."""

    def allow_live_attempt(self, fingerprint: str) -> bool:
        del fingerprint
        return True


class FingerprintCooldown:
    """Optional same-fingerprint cooldown. Not a login quota."""

    def __init__(self, *, max_attempts: int = 1) -> None:
        self._max_attempts = max_attempts
        self._hits: dict[str, int] = {}
        self._lock = Lock()

    def allow_live_attempt(self, fingerprint: str) -> bool:
        with self._lock:
            used = self._hits.get(fingerprint, 0)
            if used >= self._max_attempts:
                return False
            self._hits[fingerprint] = used + 1
            return True
