"""Stable request fingerprints for cache, replay, and partition identity."""

from __future__ import annotations

import hashlib
import json
from typing import Any

from app.integrations.fortyguard.temporal_modes import to_filter_type
from app.integrations.fortyguard.transport_models import ADAPTER_VERSION, HeatmapFetchRequest


def canonical_request_document(
    *,
    endpoint: str,
    aoi: dict[str, Any],
    local_valid_time: str | None,
    temporal_mode: str,
    granularity: int,
    filter_params: dict[str, Any],
    adapter_version: str = ADAPTER_VERSION,
) -> dict[str, Any]:
    return {
        "adapter_version": adapter_version,
        "aoi": aoi,
        "endpoint": endpoint,
        "filter_params": filter_params,
        "granularity": granularity,
        "local_valid_time": local_valid_time,
        "temporal_mode": temporal_mode,
    }


def fingerprint_request(
    *,
    endpoint: str,
    aoi: dict[str, Any],
    local_valid_time: str | None,
    temporal_mode: str,
    granularity: int,
    filter_params: dict[str, Any],
    adapter_version: str = ADAPTER_VERSION,
) -> str:
    doc = canonical_request_document(
        endpoint=endpoint,
        aoi=aoi,
        local_valid_time=local_valid_time,
        temporal_mode=temporal_mode,
        granularity=granularity,
        filter_params=filter_params,
        adapter_version=adapter_version,
    )
    blob = json.dumps(doc, sort_keys=True, separators=(",", ":"), ensure_ascii=True, default=str)
    return hashlib.sha256(blob.encode("utf-8")).hexdigest()


def heatmap_filter_params(request: HeatmapFetchRequest) -> dict[str, Any]:
    return {
        "analytic_type": request.analytic_type,
        "direction": request.direction,
        "end_date": request.end_date,
        "end_time": request.end_time,
        "filter_type": to_filter_type(request.temporal_mode),
        "threshold": request.threshold,
    }


def heatmap_fingerprint(
    request: HeatmapFetchRequest,
    *,
    aoi: dict[str, Any] | None = None,
    adapter_version: str = ADAPTER_VERSION,
    endpoint: str = "/v1/heatmap",
) -> str:
    mode = (
        request.temporal_mode.value
        if hasattr(request.temporal_mode, "value")
        else str(request.temporal_mode)
    )
    return fingerprint_request(
        endpoint=endpoint,
        aoi=aoi if aoi is not None else request.polygon_aoi,
        local_valid_time=request.local_valid_time_label(),
        temporal_mode=mode,
        granularity=int(request.granularity),
        filter_params=heatmap_filter_params(request),
        adapter_version=adapter_version,
    )
