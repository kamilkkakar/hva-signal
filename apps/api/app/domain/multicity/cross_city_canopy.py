"""Cross-city canopy contract kept separate from Phoenix local canopy."""

from __future__ import annotations

from typing import Any, Final

CROSS_CITY_CANOPY_CONTRACT_V1: Final = "CROSS_CITY_CANOPY_CONTRACT_V1"
CROSS_CITY_CANOPY_STATUS: Final = "READY_FOR_ACQUISITION"

_SELECTION: Final[dict[str, Any]] = {
    "contract_version": CROSS_CITY_CANOPY_CONTRACT_V1,
    "status": CROSS_CITY_CANOPY_STATUS,
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


def cross_city_canopy_contract() -> dict[str, Any]:
    return dict(_SELECTION)


__all__ = [
    "CROSS_CITY_CANOPY_CONTRACT_V1",
    "CROSS_CITY_CANOPY_STATUS",
    "cross_city_canopy_contract",
]
