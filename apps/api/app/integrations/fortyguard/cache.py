"""L1 memory + L2 disk cache keyed by request fingerprint.

Disk root defaults to .cache/fortyguard (gitignored). Never persist API keys.
Historical results are immutable (no TTL). Operational/forecast results expire.
"""

from __future__ import annotations

import json
from collections.abc import Callable
from datetime import date, datetime, timedelta, timezone
from pathlib import Path
from typing import Any

_SECRET_KEYS = {
    "api-key",
    "api_key",
    "authorization",
    "x-api-key",
    "fortyguard_api_key",
    "cookie",
    "set-cookie",
}

_ENVELOPE = "fortyguard-l2-v1"
OPERATIONAL_TTL_SECONDS = 15 * 60


def redact_secrets(obj: Any) -> Any:
    if isinstance(obj, dict):
        out: dict[str, Any] = {}
        for key, value in obj.items():
            lowered = str(key).lower()
            if lowered in _SECRET_KEYS or "api_key" in lowered or lowered == "key":
                continue
            out[key] = redact_secrets(value)
        return out
    if isinstance(obj, list):
        return [redact_secrets(item) for item in obj]
    return obj


def operational_ttl_seconds(start_date: str, *, today: date | None = None) -> int | None:
    """TTL for current/forward heatmaps. Past dates are treated as historical."""
    if not start_date:
        return OPERATIONAL_TTL_SECONDS
    try:
        day = date.fromisoformat(start_date)
    except ValueError:
        return OPERATIONAL_TTL_SECONDS
    today = today or datetime.now(timezone.utc).date()
    if day >= today:
        return OPERATIONAL_TTL_SECONDS
    return None


def ttl_for_heatmap_payload(payload: dict[str, Any], *, today: date | None = None) -> int | None:
    """Read start_date from a heatmap POST body (`date_time.start_date`)."""
    date_time = payload.get("date_time") if isinstance(payload.get("date_time"), dict) else {}
    start = date_time.get("start_date") or payload.get("start_date") or ""
    return operational_ttl_seconds(str(start), today=today)


class FortyGuardCache:
    def __init__(
        self,
        disk_dir: str | Path = ".cache/fortyguard",
        *,
        now: Callable[[], datetime] | None = None,
    ) -> None:
        self.disk_dir = Path(disk_dir)
        self._l1: dict[str, Any] = {}
        self._now = now or (lambda: datetime.now(timezone.utc))

    def _expired(self, record: dict[str, Any]) -> bool:
        ttl = record.get("ttl_seconds")
        if ttl is None:
            return False
        cached_at = datetime.fromisoformat(str(record["cached_at"]))
        if cached_at.tzinfo is None:
            cached_at = cached_at.replace(tzinfo=timezone.utc)
        return self._now() - cached_at >= timedelta(seconds=int(ttl))

    def _unwrap(self, record: Any) -> Any:
        if isinstance(record, dict) and record.get("_cache") == _ENVELOPE:
            return record["payload"]
        return record

    def get(self, fingerprint: str) -> tuple[Any, str] | None:
        if fingerprint in self._l1:
            record = self._l1[fingerprint]
            if isinstance(record, dict) and record.get("_cache") == _ENVELOPE:
                if self._expired(record):
                    del self._l1[fingerprint]
                    path = self.disk_dir / f"{fingerprint}.json"
                    if path.is_file():
                        path.unlink()
                    return None
            return self._unwrap(record), "l1"
        path = self.disk_dir / f"{fingerprint}.json"
        if path.is_file():
            record = json.loads(path.read_text(encoding="utf-8"))
            record = redact_secrets(record)
            if isinstance(record, dict) and record.get("_cache") == _ENVELOPE:
                if self._expired(record):
                    path.unlink()
                    return None
            self._l1[fingerprint] = record
            return self._unwrap(record), "l2"
        return None

    def put(
        self,
        fingerprint: str,
        payload: Any,
        *,
        ttl_seconds: int | None = None,
    ) -> None:
        redacted = redact_secrets(payload)
        record = {
            "_cache": _ENVELOPE,
            "cached_at": self._now().isoformat(),
            "ttl_seconds": ttl_seconds,
            "payload": redacted,
        }
        self._l1[fingerprint] = record
        self.disk_dir.mkdir(parents=True, exist_ok=True)
        path = self.disk_dir / f"{fingerprint}.json"
        path.write_text(json.dumps(record, default=str), encoding="utf-8")
