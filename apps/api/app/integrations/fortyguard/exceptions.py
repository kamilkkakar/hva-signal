"""Typed FortyGuard adapter errors. Do not put API keys in messages."""

from __future__ import annotations


class FortyGuardAdapterError(Exception):
    """Base error for the FortyGuard adapter."""


class MissingApiKeyError(FortyGuardAdapterError):
    """LIVE access was requested but no API key is configured."""


class FortyGuardHttpError(FortyGuardAdapterError):
    def __init__(self, message: str, status_code: int | None = None) -> None:
        self.status_code = status_code
        super().__init__(message)


class ActivityNotReadyError(FortyGuardAdapterError):
    """Status endpoint returned 404 while the activity propagates."""

    def __init__(self, activity_id: str) -> None:
        self.activity_id = activity_id
        super().__init__(
            f"Activity {activity_id} is not visible yet (status endpoint returned 404)."
        )


class TaskFailedError(FortyGuardAdapterError):
    """Upstream activity terminated in a failure state."""


class TaskTimeoutError(FortyGuardAdapterError):
    """Polling budget exhausted before a terminal status."""


class ReplayFixtureNotFoundError(FortyGuardAdapterError):
    def __init__(self, fingerprint: str) -> None:
        self.fingerprint = fingerprint
        super().__init__(f"No replay fixture for fingerprint {fingerprint}.")
