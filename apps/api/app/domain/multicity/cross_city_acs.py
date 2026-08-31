"""Load packaged cross-city ACS context rows."""

from __future__ import annotations

import json
from functools import lru_cache
from pathlib import Path
from typing import Any


def _repo_root() -> Path:
    return Path(__file__).resolve().parents[5]


@lru_cache(maxsize=8)
def load_city_acs(city_id: str) -> dict[str, Any]:
    path = _repo_root() / "data" / "context" / "cross-city" / f"{city_id}.json"
    if not path.is_file():
        return {"rows": {}}
    return json.loads(path.read_text(encoding="utf-8"))


def acs_metric(city_id: str, geoid: str, field: str) -> float | None:
    rows = load_city_acs(city_id).get("rows") or {}
    row = rows.get(geoid) or rows.get(geoid.zfill(11))
    if not isinstance(row, dict):
        return None
    metric = row.get(field)
    if not isinstance(metric, dict):
        return None
    value = metric.get("estimate")
    return float(value) if value is not None else None


def acs_share_pct(city_id: str, geoid: str, field: str) -> float | None:
    """Return share_of_units / share_of_households as a 0–100 percentage."""
    rows = load_city_acs(city_id).get("rows") or {}
    row = rows.get(geoid) or rows.get(geoid.zfill(11))
    if not isinstance(row, dict):
        return None
    metric = row.get(field)
    if not isinstance(metric, dict):
        return None
    share = metric.get("share_of_units")
    if share is None:
        share = metric.get("share_of_households")
    if share is None:
        return None
    return float(share) * 100.0


__all__ = ["acs_metric", "acs_share_pct", "load_city_acs"]
