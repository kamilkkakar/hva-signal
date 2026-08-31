"""Cross-city canopy contract + materialized NLCD values."""

from __future__ import annotations

import json
from functools import lru_cache
from pathlib import Path
from typing import Any, Final

CROSS_CITY_CANOPY_CONTRACT_V1: Final = "CROSS_CITY_CANOPY_CONTRACT_V1"
CROSS_CITY_CANOPY_STATUS: Final = "MATERIALIZED"


def _repo_root() -> Path:
    return Path(__file__).resolve().parents[5]


def _contract_path() -> Path:
    return _repo_root() / "data" / "context" / "cross-city" / "canopy" / "CONTRACT.json"


def cross_city_canopy_contract() -> dict[str, Any]:
    path = _contract_path()
    if path.is_file():
        doc = json.loads(path.read_text(encoding="utf-8"))
        doc.setdefault("contract_version", CROSS_CITY_CANOPY_CONTRACT_V1)
        doc.setdefault("silent_substitute_forbidden", True)
        return doc
    return {
        "contract_version": CROSS_CITY_CANOPY_CONTRACT_V1,
        "status": "READY_FOR_ACQUISITION",
        "source_selected": (
            "NLCD / USDA Forest Service Percent Tree Canopy Cover (Tree Canopy Cover, CONUS)"
        ),
        "definition": (
            "Percent of each 30 m raster cell covered by tree canopy, derived from "
            "satellite imagery plus ancillary information."
        ),
        "vintage": "2021 NLCD TCC for comparable four-city baseline",
        "resolution": "30 m raster",
        "aggregation_to_tracts": (
            "Area-weighted zonal mean of pixel canopy percentages across tract polygons."
        ),
        "all_four_cities_supported": True,
        "phoenix_local_canopy_difference": (
            "Phoenix local canopy uses OHR shade-study TREE_PCT_N over plantable ground; "
            "that is not the same denominator as national total-land canopy."
        ),
        "comparison_defensible": True,
        "silent_substitute_forbidden": True,
    }


@lru_cache(maxsize=8)
def load_city_canopy(city_id: str) -> dict[str, Any]:
    path = _repo_root() / "data" / "context" / "cross-city" / "canopy" / f"{city_id}.json"
    if not path.is_file():
        return {"rows": {}}
    return json.loads(path.read_text(encoding="utf-8"))


def canopy_pct_for(city_id: str, geoid: str) -> float | None:
    rows = load_city_canopy(city_id).get("rows") or {}
    row = rows.get(geoid) or rows.get(geoid.zfill(11))
    if not isinstance(row, dict):
        return None
    value = row.get("cross_city_tree_canopy_pct")
    return float(value) if value is not None else None


__all__ = [
    "CROSS_CITY_CANOPY_CONTRACT_V1",
    "CROSS_CITY_CANOPY_STATUS",
    "canopy_pct_for",
    "cross_city_canopy_contract",
    "load_city_canopy",
]
