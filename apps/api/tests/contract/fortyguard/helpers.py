from __future__ import annotations

from pathlib import Path
from typing import Any

from app.integrations.fortyguard.transport_models import (
    DataMode,
    HeatmapFetchRequest,
    HeatmapTemporalMode,
)

# Downtown Phoenix probe AOI from the live 2024-07-15 hourly tcm call.
PHOENIX_HOURLY_AOI: dict[str, Any] = {
    "type": "Polygon",
    "coordinates": [
        [
            [-112.07831888657297, 33.4447963963964],
            [-112.06968111342702, 33.4447963963964],
            [-112.06968111342702, 33.4520036036036],
            [-112.07831888657297, 33.4520036036036],
            [-112.07831888657297, 33.4447963963964],
        ]
    ],
}

FIXTURE_DIR = Path(__file__).resolve().parents[2] / "fixtures" / "fortyguard"
HOURLY_TCM_FIXTURE = FIXTURE_DIR / "heatmap_tcm_hourly_1500.json"


def hourly_tcm_request(**overrides: Any) -> HeatmapFetchRequest:
    payload: dict[str, Any] = {
        "polygon_aoi": PHOENIX_HOURLY_AOI,
        "start_date": "2024-07-15",
        "start_time": "15:00",
        "temporal_mode": HeatmapTemporalMode.SINGLE_HOUR,
        "granularity": 100,
        "analytic_type": "tcm",
        "data_mode": DataMode.REPLAY,
    }
    payload.update(overrides)
    return HeatmapFetchRequest.model_validate(payload)


def request_from_fixture(doc: dict, **overrides: Any) -> HeatmapFetchRequest:
    meta_req = dict(doc["meta"]["request"])
    meta_req.setdefault("temporal_mode", HeatmapTemporalMode.SINGLE_HOUR)
    meta_req.setdefault("data_mode", DataMode.REPLAY)
    meta_req.update(overrides)
    return HeatmapFetchRequest.model_validate(meta_req)
