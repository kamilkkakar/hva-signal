"""Pure job / request identity. No vendor I/O. No public route."""

from __future__ import annotations

import hashlib
import json
from datetime import datetime
from typing import Any

from app.services.snapshot_identity import (
    require_requested_hour,
    snapshot_request_fingerprint,
)

HISTORICAL_IDENTITY_VERSION = "hva-signal-a-historical-identity-v1"
TWO_SIGNAL_JOB_IDENTITY_VERSION = "hva-signal-two-signal-job-identity-v1"


def _digest(document: dict[str, Any]) -> str:
    blob = json.dumps(document, sort_keys=True, separators=(",", ":"), ensure_ascii=True)
    return hashlib.sha256(blob.encode("utf-8")).hexdigest()


def historical_request_fingerprint(
    *,
    area_id: str,
    analysis_time: datetime,
    timezone: str,
    analysis_mode: str,
    granularity_m: int,
    data_mode: str,
    geometry_sha256: str,
    zone_geometry_version: str,
    reference_protocol_id: str,
    area_config_version: str,
) -> str:
    """Signal A identity. Includes reference protocol; does not include Signal B hour."""
    hour = analysis_time
    if hour.tzinfo is not None:
        raise ValueError("historical analysis_time must be AOI-local naive")
    document = {
        "identity_version": HISTORICAL_IDENTITY_VERSION,
        "area_id": area_id,
        "analysis_time": hour.isoformat(timespec="seconds"),
        "timezone": timezone,
        "analysis_mode": analysis_mode,
        "granularity_m": int(granularity_m),
        "data_mode": data_mode,
        "geometry_sha256": geometry_sha256,
        "zone_geometry_version": zone_geometry_version,
        "reference_protocol_id": reference_protocol_id,
        "area_config_version": area_config_version,
    }
    return _digest(document)


def two_signal_job_fingerprint(
    *,
    area_id: str,
    geometry_sha256: str,
    request_historical: bool,
    request_selected_time: bool,
    historical_fingerprint: str | None = None,
    selected_time_fingerprint: str | None = None,
) -> str:
    """Join key for a two-signal job. A and B identities stay separable."""
    if request_historical and not historical_fingerprint:
        raise ValueError("historical fingerprint is required when Signal A is requested")
    if request_selected_time and not selected_time_fingerprint:
        raise ValueError("snapshot fingerprint is required when Signal B is requested")
    document = {
        "identity_version": TWO_SIGNAL_JOB_IDENTITY_VERSION,
        "area_id": area_id,
        "geometry_sha256": geometry_sha256,
        "request_historical": request_historical,
        "request_selected_time": request_selected_time,
        "historical_fingerprint": historical_fingerprint if request_historical else None,
        "selected_time_fingerprint": (
            selected_time_fingerprint if request_selected_time else None
        ),
    }
    return _digest(document)


def snapshot_fingerprint_ignores_reference_protocol() -> bool:
    """Documented invariant: preparing Signal A must not change the B key."""
    return "reference" not in snapshot_request_fingerprint.__code__.co_varnames


def require_snapshot_hour(timestamp: datetime) -> datetime:
    return require_requested_hour(timestamp)
