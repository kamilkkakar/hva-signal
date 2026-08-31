"""Load acquired CROSS_CITY_OBSERVATION_V1 zone means (runtime-safe)."""

from __future__ import annotations

import json
from functools import lru_cache
from pathlib import Path
from typing import Any


def _repo_root() -> Path:
    return Path(__file__).resolve().parents[5]


@lru_cache(maxsize=8)
def load_city_thermal_zones(city_id: str) -> dict[str, Any] | None:
    path = (
        _repo_root()
        / "data"
        / "acquisitions"
        / "cross-city"
        / city_id
        / "normalized"
        / "zone_means.json"
    )
    if not path.is_file():
        return None
    return json.loads(path.read_text(encoding="utf-8"))


def thermal_mean_c_for(city_id: str, geoid: str) -> float | None:
    doc = load_city_thermal_zones(city_id)
    if not doc:
        return None
    rows = (doc.get("aggregation") or {}).get("rows") or []
    needle = geoid.zfill(11)
    for row in rows:
        if not isinstance(row, dict):
            continue
        rid = str(row.get("tract_geoid") or row.get("area_id") or "").zfill(11)
        if rid == needle and row.get("usable") and row.get("mean_tcm_c") is not None:
            return float(row["mean_tcm_c"])
    return None


__all__ = ["load_city_thermal_zones", "thermal_mean_c_for"]
