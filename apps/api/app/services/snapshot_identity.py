"""Canonical Signal B request identity. No vendor I/O. No reference protocol ID."""

from __future__ import annotations

import hashlib
import json
from datetime import datetime
from typing import Any

SNAPSHOT_IDENTITY_VERSION = "hva-signal-b-snapshot-identity-v1"


def require_requested_hour(timestamp: datetime) -> datetime:
    """AOI-local naive hour. Rejects timezone-aware values and non-zero minutes."""
    if timestamp.tzinfo is not None:
        raise ValueError("selected-time timestamp must be AOI-local naive, not timezone-aware")
    if timestamp.minute != 0 or timestamp.second != 0 or timestamp.microsecond != 0:
        raise ValueError("arbitrary minutes are unsupported; do not silently round")
    return timestamp


def require_dst_safe_requested_hour(timestamp: datetime, timezone: str) -> datetime:
    """Future Signal B guard. Naive hour plus frozen-candidate DST uniqueness."""
    from app.services.aoi_timezone import require_unique_aoi_local_hour

    hour = require_requested_hour(timestamp)
    return require_unique_aoi_local_hour(hour, timezone)


def snapshot_request_document(
    *,
    area_id: str,
    geometry_sha256: str,
    zone_geometry_version: str,
    target_timestamp: datetime,
    timezone: str,
    analytic: str,
    granularity_m: int,
    aggregation_spec_version: str,
    temporal_mode: str = "single_hour",
    adapter_version: str | None = None,
) -> dict[str, Any]:
    hour = require_dst_safe_requested_hour(target_timestamp, timezone)
    return {
        "identity_version": SNAPSHOT_IDENTITY_VERSION,
        "area_id": area_id,
        "geometry_sha256": geometry_sha256,
        "zone_geometry_version": zone_geometry_version,
        "target_local_timestamp": hour.isoformat(timespec="seconds"),
        "timezone": timezone,
        "analytic": analytic,
        "granularity_m": int(granularity_m),
        "aggregation_spec_version": aggregation_spec_version,
        "temporal_mode": temporal_mode,
        "adapter_version": adapter_version,
    }


def snapshot_request_fingerprint(
    *,
    area_id: str,
    geometry_sha256: str,
    zone_geometry_version: str,
    target_timestamp: datetime,
    timezone: str,
    analytic: str = "tcm",
    granularity_m: int = 100,
    aggregation_spec_version: str,
    temporal_mode: str = "single_hour",
    adapter_version: str | None = None,
) -> str:
    """Cache / dedupe / job-join key. Omits historical reference identity."""
    doc = snapshot_request_document(
        area_id=area_id,
        geometry_sha256=geometry_sha256,
        zone_geometry_version=zone_geometry_version,
        target_timestamp=target_timestamp,
        timezone=timezone,
        analytic=analytic,
        granularity_m=granularity_m,
        aggregation_spec_version=aggregation_spec_version,
        temporal_mode=temporal_mode,
        adapter_version=adapter_version,
    )
    blob = json.dumps(doc, sort_keys=True, separators=(",", ":"), ensure_ascii=True)
    return hashlib.sha256(blob.encode("utf-8")).hexdigest()
