"""Map HeatmapTemporalMode to FortyGuard filter_type 1-4."""

from __future__ import annotations

from datetime import date, timedelta
from typing import Any

from app.integrations.fortyguard.transport_models import HeatmapFetchRequest, HeatmapTemporalMode

_FILTER_TYPE: dict[str, int] = {
    HeatmapTemporalMode.SINGLE_HOUR.value: 1,
    HeatmapTemporalMode.HOUR_RANGE.value: 2,
    HeatmapTemporalMode.FULL_DAY.value: 3,
    HeatmapTemporalMode.DAY_RANGE.value: 4,
    HeatmapTemporalMode.MONTH.value: 4,
}


def to_filter_type(mode: HeatmapTemporalMode | str) -> int:
    value = mode.value if hasattr(mode, "value") else str(mode)
    try:
        return _FILTER_TYPE[value]
    except KeyError as exc:
        raise ValueError(f"Unknown HeatmapTemporalMode {value!r}") from exc


def build_heatmap_payload(request: HeatmapFetchRequest) -> dict[str, Any]:
    """Build the POST /v1/heatmap body. start_time is copied as an AOI-local string."""
    filter_type = to_filter_type(request.temporal_mode)
    date_time: dict[str, Any] = {
        "start_date": request.start_date,
        "filter_type": filter_type,
    }
    if request.start_time is not None:
        date_time["start_time"] = request.start_time
    if request.end_time is not None:
        date_time["end_time"] = request.end_time
    end_date = request.end_date
    mode_value = (
        request.temporal_mode.value
        if hasattr(request.temporal_mode, "value")
        else str(request.temporal_mode)
    )
    if end_date is None and mode_value == HeatmapTemporalMode.MONTH.value:
        start = date.fromisoformat(request.start_date)
        end_date = (start + timedelta(days=30)).isoformat()
    if end_date is not None:
        date_time["end_date"] = end_date

    payload: dict[str, Any] = {
        "polygon_aoi": request.polygon_aoi,
        "date_time": date_time,
        "granularity": request.granularity,
        "analytic_type": request.analytic_type,
    }
    if request.threshold is not None:
        payload["threshold"] = request.threshold
    if request.direction is not None:
        payload["direction"] = request.direction
    return payload
