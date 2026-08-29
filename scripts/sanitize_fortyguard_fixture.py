"""Sanitize a FortyGuard cache payload into a committed replay fixture.

Strips headers, API keys, and bulky unused blobs. Keeps a handful of tiles
plus temperature_stats. Never writes FORTYGUARD_API_KEY.
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Any

REPO_ROOT = Path(__file__).resolve().parents[1]
API_ROOT = REPO_ROOT / "apps" / "api"
if str(API_ROOT) not in sys.path:
    sys.path.insert(0, str(API_ROOT))

from app.integrations.fortyguard.cache import redact_secrets  # noqa: E402
from app.integrations.fortyguard.fingerprints import heatmap_fingerprint  # noqa: E402
from app.integrations.fortyguard.transport_models import (  # noqa: E402
    ADAPTER_VERSION,
    DataMode,
    HeatmapFetchRequest,
    HeatmapTemporalMode,
)

DEFAULT_INPUT = (
    REPO_ROOT
    / "workforce"
    / "context"
    / "05_code"
    / "cache"
    / "v1_heatmap__dbb3d3d6fdd918d24190.json"
)
DEFAULT_OUTPUT = (
    API_ROOT / "tests" / "fixtures" / "fortyguard" / "heatmap_tcm_hourly_1500.json"
)

# Call-log request for the default hourly Phoenix tcm fixture (AOI-local 15:00).
DEFAULT_REQUEST: dict[str, Any] = {
    "polygon_aoi": {
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
    },
    "start_date": "2024-07-15",
    "start_time": "15:00",
    "end_time": None,
    "end_date": None,
    "filter_type": 1,
    "granularity": 100,
    "analytic_type": "tcm",
    "temporal_mode": "single_hour",
    "threshold": None,
    "direction": None,
}

_DROP_STATS = {
    "overall_temperature_distribution",
    "normal_temperature_distribution",
    "temperature_frequency",
}


def _filter_type_to_mode(filter_type: int | None, fallback: str) -> str:
    return {
        1: HeatmapTemporalMode.SINGLE_HOUR.value,
        2: HeatmapTemporalMode.HOUR_RANGE.value,
        3: HeatmapTemporalMode.FULL_DAY.value,
        4: HeatmapTemporalMode.DAY_RANGE.value,
    }.get(filter_type or 0, fallback)


def sanitize_document(
    raw: dict[str, Any],
    *,
    request: dict[str, Any],
    max_tiles: int = 5,
    source_name: str = "",
    label: str = "",
) -> dict[str, Any]:
    cleaned = redact_secrets(raw)
    cleaned.pop("headers", None)
    result = dict(cleaned.get("result") or cleaned)
    map_data = dict(result.get("map_data") or {})
    features = list(map_data.get("features") or [])[: max(0, max_tiles)]
    map_data["features"] = features
    if "type" not in map_data:
        map_data["type"] = "FeatureCollection"
    stats = dict(result.get("stats_data") or {})
    for blob in _DROP_STATS:
        stats.pop(blob, None)
    result["map_data"] = map_data
    result["stats_data"] = stats

    mode = request.get("temporal_mode") or _filter_type_to_mode(
        request.get("filter_type"), HeatmapTemporalMode.SINGLE_HOUR.value
    )
    fetch = HeatmapFetchRequest.model_validate(
        {
            "polygon_aoi": request["polygon_aoi"],
            "start_date": request["start_date"],
            "start_time": request.get("start_time"),
            "end_time": request.get("end_time"),
            "end_date": request.get("end_date"),
            "temporal_mode": mode,
            "granularity": request.get("granularity", 100),
            "analytic_type": request.get("analytic_type", "tcm"),
            "threshold": request.get("threshold"),
            "direction": request.get("direction"),
            "data_mode": DataMode.REPLAY,
        }
    )
    fingerprint = heatmap_fingerprint(fetch)
    meta_request = {
        "polygon_aoi": fetch.polygon_aoi,
        "start_date": fetch.start_date,
        "start_time": fetch.start_time,
        "end_time": fetch.end_time,
        "end_date": fetch.end_date,
        "filter_type": request.get("filter_type", 1),
        "granularity": fetch.granularity,
        "analytic_type": fetch.analytic_type,
        "temporal_mode": mode,
        "threshold": fetch.threshold,
        "direction": fetch.direction,
    }
    return {
        "meta": {
            "sanitized": True,
            "source_cache": source_name,
            "label": label,
            "temperature_unit": "celsius",
            "adapter_version": ADAPTER_VERSION,
            "endpoint": "/v1/heatmap",
            "request": meta_request,
            "fingerprint": fingerprint,
        },
        "activity_id": "sanitized-replay",
        "result": result,
    }


def _write_index(output: Path, fingerprint: str) -> None:
    index_path = output.parent / "index.json"
    index: dict[str, Any] = {"by_fingerprint": {}}
    if index_path.is_file():
        index = json.loads(index_path.read_text(encoding="utf-8"))
        index.setdefault("by_fingerprint", {})
    index["by_fingerprint"][fingerprint] = output.name
    index_path.write_text(json.dumps(index, indent=2) + "\n", encoding="utf-8")


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--input", type=Path, default=DEFAULT_INPUT)
    parser.add_argument("--output", type=Path, default=DEFAULT_OUTPUT)
    parser.add_argument("--max-tiles", type=int, default=5)
    parser.add_argument("--label", default="probe_hourly_1500")
    parser.add_argument(
        "--request-json",
        type=Path,
        default=None,
        help="Optional JSON file with the original request fields.",
    )
    args = parser.parse_args(argv)

    raw = json.loads(args.input.read_text(encoding="utf-8"))
    request = DEFAULT_REQUEST
    if args.request_json:
        request = json.loads(args.request_json.read_text(encoding="utf-8"))
    doc = sanitize_document(
        raw,
        request=request,
        max_tiles=args.max_tiles,
        source_name=args.input.name,
        label=args.label,
    )
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(doc, indent=2) + "\n", encoding="utf-8")
    _write_index(args.output, doc["meta"]["fingerprint"])
    print(f"Wrote {args.output} ({len(doc['result']['map_data']['features'])} tiles)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
