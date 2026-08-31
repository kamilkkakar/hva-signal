"""Cross-city validation package V2 — preflight only, zero vendor calls."""

from __future__ import annotations

import json
from datetime import datetime
from pathlib import Path
from typing import Any, Mapping

from app.domain.multicity.city_catalog import resolve_city_aoi
from app.domain.multicity.observation_clock import (
    CROSS_CITY_OBSERVATION_V1,
    resolve_city_observation_clock,
)
from app.domain.multicity.type1_live import dry_run_type1_preflight
from app.integrations.fortyguard.partitioning import polygon_area_km2

CROSS_CITY_VALIDATION_PACKAGE_V2 = "CROSS_CITY_VALIDATION_PACKAGE_V2"
TARGET_LOCAL_TIMESTAMP = datetime(2024, 7, 8, 15, 0, 0)
PHOENIX_REUSE_ACTIVITY_ID = "92086c4c-1550-4263-8ac8-9a6c9e030bc4"
CALLS_ACTUALLY_MADE = 0

# Empirical Phoenix Type-1 observation (sanity check only — not a vendor quote).
EMPIRICAL_PHOENIX = {
    "activity_id": PHOENIX_REUSE_ACTIVITY_ID,
    "tiles_returned": 3749,
    "approx_debit_credits": 4220,
    "partitions": 1,
    "resolution_m": 100,
    "debit_per_tile": round(4220 / 3749, 4),
    "debit_per_partition": 4220,
    "note": (
        "Single-observation ratios. NOT a universal provider rate. "
        "NOT a vendor quote for other cities."
    ),
}

PHOENIX_REUSE_PROOF = {
    "activity_id": PHOENIX_REUSE_ACTIVITY_ID,
    "reusable": "NO",
    "tracts_fully_covered": "0 / 25",
    "tracts_partially_covered": 0,
    "tracts_not_covered": 25,
    "approx_100m_cell_coverage_ratio": 0.0,
    "new_phoenix_call_needed": True,
    "reason": (
        "Existing phoenix-demo surface and CROSS_CITY_COMPARISON_GEOGRAPHY_V1 Phoenix "
        "share zero tracts and zero spatial overlap."
    ),
}


def _repo_root() -> Path:
    return Path(__file__).resolve().parents[5]


def _load_freeze(city_id: str) -> dict[str, Any]:
    path = _repo_root() / "data" / "areas" / "cross-city" / city_id / "freeze.json"
    return json.loads(path.read_text(encoding="utf-8"))


def _empirical_sanity(*, expected_tiles: int, partitions: int, area_km2: float) -> dict[str, Any]:
    per_tile = EMPIRICAL_PHOENIX["debit_per_tile"]
    low = int(round(expected_tiles * per_tile * 0.7))
    mid = int(round(expected_tiles * per_tile))
    high = int(round(expected_tiles * per_tile * 1.5 + partitions * 50))
    return {
        "estimate_type": "EMPIRICAL_SANITY_CHECK",
        "phoenix_scaled_mid": mid,
        "phoenix_scaled_range": [low, high],
        "conservative_upper_bound": high,
        "confidence": "LOW",
        "basis": (
            f"scaled from Phoenix ~{EMPIRICAL_PHOENIX['approx_debit_credits']} debit / "
            f"{EMPIRICAL_PHOENIX['tiles_returned']} tiles; area={area_km2} km2"
        ),
    }


def _city_plan(city_name: str, city_id: str, *, new_call: bool) -> dict[str, Any]:
    freeze = _load_freeze(city_id)
    preflight = dry_run_type1_preflight(
        {
            "city": city_name,
            "target_local": TARGET_LOCAL_TIMESTAMP,
            "key_alias": "VALIDATION_B",
        }
    )
    clock = resolve_city_observation_clock(city_id)
    provider = freeze["provider_request"]
    complexity = preflight["local_complexity_estimate"]
    sanity = _empirical_sanity(
        expected_tiles=int(provider["expected_provider_cells_tiles_union"]),
        partitions=int(provider["partitions"]),
        area_km2=float(provider["analysis_union_area_km2"]),
    )
    return {
        "city": city_name,
        "city_id": city_id,
        "mode": "PROPOSED_NEW_TYPE1" if new_call else "REUSE_EXISTING_ACTIVITY",
        "new_vendor_call_required": new_call,
        "activity_id": None if new_call else PHOENIX_REUSE_ACTIVITY_ID,
        "phoenix_reuse": "NO" if city_id == "phoenix" else "N/A",
        "final_analysis_geography_version": freeze["analysis_geography_version"],
        "final_comparison_geography_version": freeze["selection_policy_version"],
        "analysis_area_km2": provider["analysis_union_area_km2"],
        "provider_request_area_km2": provider["provider_request_area_km2"],
        "bounding_envelope_area_km2": provider["bounding_envelope_area_km2"],
        "overhead_envelope_vs_union_pct": round(
            (provider["overhead_ratio_envelope_vs_union"] - 1.0) * 100.0, 2
        )
        if provider.get("overhead_ratio_envelope_vs_union")
        else None,
        "partitions": provider["partitions"],
        "expected_tile_cell_count": provider["expected_provider_cells_tiles_union"],
        "local_time": clock.local_timestamp,
        "provider_time": clock.provider_payload_local_valid_time,
        "utc_timestamp": clock.utc_timestamp,
        "dst_active": clock.dst_active,
        "request_fingerprint": preflight["request_fingerprint"],
        "cache_fingerprint": preflight["cache_fingerprint"],
        "key_alias": "VALIDATION_B",
        "cost_model_output": complexity,
        "empirical_sanity": sanity,
        "conservative_upper_bound": sanity["conservative_upper_bound"],
        "confidence": sanity["confidence"],
        "preflight": preflight,
        "freeze": {
            "combined_geometry_hash": freeze["combined_geometry_hash"],
            "area_config_hash": freeze["area_config_hash"],
            "analysis_area_count": freeze["analysis_area_count"],
            "exact_tract_geoids": freeze["exact_tract_geoids"],
        },
    }


def build_cross_city_validation_package() -> dict[str, Any]:
    """V2 builder. Phoenix requires a NEW call — reuse proof failed."""
    cities = [
        _city_plan("Phoenix", "phoenix", new_call=True),
        _city_plan("Las Vegas", "las_vegas", new_call=True),
        _city_plan("Tucson", "tucson", new_call=True),
        _city_plan("Los Angeles", "los_angeles", new_call=True),
    ]
    total_upper = sum(int(item["conservative_upper_bound"]) for item in cities)
    return {
        "package_version": CROSS_CITY_VALIDATION_PACKAGE_V2,
        "observation_contract": CROSS_CITY_OBSERVATION_V1,
        "target_local": TARGET_LOCAL_TIMESTAMP.isoformat(timespec="seconds"),
        "calls_actually_made": CALLS_ACTUALLY_MADE,
        "phoenix_reuse_proof": PHOENIX_REUSE_PROOF,
        "empirical_phoenix_calibration": EMPIRICAL_PHOENIX,
        "local_complexity_disclaimer": (
            "local_complexity_units are NOT vendor credits; historical 39/52/102 "
            "values were mislabelled."
        ),
        "heuristic_formula": "partition_count + ceil(expected_tiles_estimate / 5000)",
        "cities": cities,
        "total_new_calls_required": sum(
            1 for item in cities if item["new_vendor_call_required"]
        ),
        "total_conservative_upper_bound_spend": {
            "value": total_upper,
            "units": "empirical_sanity_scaled_debit_proxy",
            "estimate_type": "EMPIRICAL_SANITY_CHECK",
            "label": "NOT_A_VENDOR_QUOTE",
            "confidence": "LOW",
            "scope": "Phoenix + Las Vegas + Tucson + Los Angeles proposed new Type-1",
        },
        "ready_for_human_authorization": False,
        "authorization_blocker": (
            "Human must authorize the four-call package after reviewing V2 footprints "
            "and empirical sanity bounds. Three-call reuse assumption is withdrawn."
        ),
    }


def render_cross_city_validation_package_markdown(
    package: Mapping[str, Any] | None = None,
) -> str:
    doc = dict(package) if package is not None else build_cross_city_validation_package()
    lines = [
        "# CROSS_CITY_VALIDATION_PACKAGE_V2",
        "",
        f"- Target local timestamp: `{doc['target_local']}`",
        f"- Observation contract: `{doc['observation_contract']}`",
        f"- Calls actually made: `{doc['calls_actually_made']}`",
        f"- Phoenix reuse: `{doc['phoenix_reuse_proof']['reusable']}` "
        f"({doc['phoenix_reuse_proof']['reason']})",
        f"- Local complexity disclaimer: {doc['local_complexity_disclaimer']}",
        "",
        "## City Plan",
        "",
    ]
    for item in doc["cities"]:
        complexity = item["cost_model_output"]["value"]
        lines.append(
            f"- {item['city']}: PROPOSED new Type-1; "
            f"analysis `{item['analysis_area_km2']}` km2; "
            f"partitions `{item['partitions']}`; "
            f"expected tiles `{item['expected_tile_cell_count']}`; "
            f"local complexity units `{complexity}` "
            f"({item['cost_model_output']['label']}); "
            f"empirical sanity upper `{item['conservative_upper_bound']}` "
            f"(NOT a vendor quote)."
        )
    total = doc["total_conservative_upper_bound_spend"]
    lines.extend(
        [
            "",
            "## Total",
            "",
            f"- Total new calls required: `{doc['total_new_calls_required']}`",
            f"- Total conservative upper-bound spend proxy: `{total['value']}` "
            f"({total['label']}; {total['estimate_type']}; confidence {total['confidence']})",
            f"- Ready for human authorization: `{doc['ready_for_human_authorization']}`",
            f"- Blocker: {doc['authorization_blocker']}",
            "",
            "## JSON",
            "",
            "```json",
            _json_pretty(doc),
            "```",
            "",
        ]
    )
    return "\n".join(lines)


def write_cross_city_validation_package_markdown(path: str | Path | None = None) -> Path:
    target = (
        Path(path)
        if path is not None
        else _repo_root() / "docs" / "product" / "CROSS_CITY_VALIDATION_PACKAGE_V2.md"
    )
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(render_cross_city_validation_package_markdown(), encoding="utf-8")
    return target


def _json_pretty(value: Mapping[str, Any]) -> str:
    return json.dumps(value, indent=2, sort_keys=True, ensure_ascii=True, default=str)


# Back-compat export used by older imports.
CROSS_CITY_VALIDATION_PACKAGE_V1 = CROSS_CITY_VALIDATION_PACKAGE_V2


__all__ = [
    "CALLS_ACTUALLY_MADE",
    "CROSS_CITY_VALIDATION_PACKAGE_V1",
    "CROSS_CITY_VALIDATION_PACKAGE_V2",
    "EMPIRICAL_PHOENIX",
    "PHOENIX_REUSE_ACTIVITY_ID",
    "PHOENIX_REUSE_PROOF",
    "TARGET_LOCAL_TIMESTAMP",
    "build_cross_city_validation_package",
    "render_cross_city_validation_package_markdown",
    "write_cross_city_validation_package_markdown",
]
