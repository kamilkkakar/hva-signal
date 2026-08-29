"""Submit/poll helper. Status 404 right after submit is retried, not failed."""

from __future__ import annotations

import time
from collections.abc import Callable
from typing import Any

from app.integrations.fortyguard.exceptions import (
    ActivityNotReadyError,
    TaskFailedError,
    TaskTimeoutError,
)

_TERMINAL_SUCCESS = frozenset({"succeeded", "completed"})
_TERMINAL_FAILURE = frozenset({"failed", "error"})


def wait_for(
    get_status: Callable[[str], dict[str, Any]],
    activity_id: str,
    *,
    poll_interval: float = 3.0,
    timeout: float = 600.0,
    sleep: Callable[[float], None] = time.sleep,
    monotonic: Callable[[], float] = time.monotonic,
) -> dict[str, Any]:
    deadline = monotonic() + timeout
    while True:
        try:
            data = get_status(activity_id)
        except ActivityNotReadyError:
            if monotonic() >= deadline:
                raise TaskTimeoutError(
                    f"Activity {activity_id} never became visible within {timeout:.0f}s"
                )
            sleep(poll_interval)
            continue
        status = str(data.get("status", "")).lower()
        if status in _TERMINAL_SUCCESS:
            result = data.get("result", data)
            return result if isinstance(result, dict) else {"result": result}
        if status in _TERMINAL_FAILURE:
            raise TaskFailedError(
                f"Activity {activity_id} failed: {data.get('message') or data}"
            )
        if monotonic() >= deadline:
            raise TaskTimeoutError(
                f"Activity {activity_id} still {status!r} after {timeout:.0f}s"
            )
        sleep(poll_interval)
