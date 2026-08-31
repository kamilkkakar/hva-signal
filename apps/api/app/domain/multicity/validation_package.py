"""Cross-city validation package for the Type-1 live architecture."""

from __future__ import annotations

from datetime import datetime
from pathlib import Path
from typing import Any, Mapping

from app.domain.multicity.type1_live import dry_run_type1_preflight

CROSS_CITY_VALIDATION_PACKAGE_V1 = "CROSS_CITY_VALIDATION_PACKAGE_V1"
TARGET_LOCAL_TIMESTAMP = datetime(2024, 7, 8, 15, 0, 0)
PHOENIX_REUSE_ACTIVITY_ID = "92086c4c-1550-4263-8ac8-9a6c9e030bc4"
CALLS_ACTUALLY_MADE = 0


def build_cross_city_validation_package() -> dict[str, Any]:
    proposed = [
        {
            "city": "Las Vegas",
            "mode": "PROPOSED_NEW_TYPE1",
            "preflight": dry_run_type1_preflight(
                {
                    "city": "Las Vegas",
                    "target_local": TARGET_LOCAL_TIMESTAMP,
                    "key_alias": "VALIDATION_B",
                }
            ),
        },
        {
            "city": "Tucson",
            "mode": "PROPOSED_NEW_TYPE1",
            "preflight": dry_run_type1_preflight(
                {
                    "city": "Tucson",
                    "target_local": TARGET_LOCAL_TIMESTAMP,
                    "key_alias": "VALIDATION_B",
                }
            ),
        },
        {
            "city": "LA",
            "mode": "PROPOSED_NEW_TYPE1",
            "preflight": dry_run_type1_preflight(
                {
                    "city": "LA",
                    "target_local": TARGET_LOCAL_TIMESTAMP,
                    "key_alias": "VALIDATION_B",
                }
            ),
        },
    ]
    total_projected_credits = sum(
        int(item["preflight"]["estimated_credits"]["value"]) for item in proposed
    )
    return {
        "package_version": CROSS_CITY_VALIDATION_PACKAGE_V1,
        "target_local": TARGET_LOCAL_TIMESTAMP.isoformat(timespec="seconds"),
        "calls_actually_made": CALLS_ACTUALLY_MADE,
        "estimated_credits_disclaimer": "ESTIMATE_NOT_VENDOR_QUOTE",
        "heuristic_formula": "partition_count + ceil(expected_tiles_estimate / 5000)",
        "cities": [
            {
                "city": "Phoenix",
                "mode": "REUSE_EXISTING_ACTIVITY",
                "activity_id": PHOENIX_REUSE_ACTIVITY_ID,
                "new_vendor_call_required": False,
                "preflight": None,
            },
            *proposed,
        ],
        "total_projected_credits": {
            "value": total_projected_credits,
            "label": "ESTIMATE_NOT_VENDOR_QUOTE",
            "scope": "Las Vegas + Tucson + LA proposed new Type-1 requests only",
        },
    }


def render_cross_city_validation_package_markdown(
    package: Mapping[str, Any] | None = None,
) -> str:
    doc = (
        dict(package)
        if package is not None
        else build_cross_city_validation_package()
    )
    lines = [
        "# CROSS_CITY_VALIDATION_PACKAGE_V1",
        "",
        f"- Target local timestamp: `{doc['target_local']}`",
        f"- Calls actually made: `{doc['calls_actually_made']}`",
        f"- Credits label: `{doc['estimated_credits_disclaimer']}`",
        f"- Heuristic: `{doc['heuristic_formula']}`",
        "",
        "## City Plan",
        "",
        f"- Phoenix: reuse activity `{PHOENIX_REUSE_ACTIVITY_ID}`; no new Type-1 call.",
    ]
    for item in doc["cities"]:
        if item["city"] == "Phoenix":
            continue
        preflight = item["preflight"]
        lines.append(
            f"- {item['city']}: PROPOSED new Type-1 preflight only; estimated "
            f"`{preflight['estimated_credits']['value']}` credits; "
            f"`{preflight['partition_count']}` partitions; "
            f"`{preflight['aoi_area_estimate_km2']}` km2 AOI estimate."
        )
    total = doc["total_projected_credits"]
    lines.extend(
        [
            "",
            "## Total",
            "",
            f"- Total projected credits: `{total['value']}` ({total['label']})",
            f"- Scope: {total['scope']}",
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
        else Path(__file__).resolve().parents[5] / "docs" / "product" / "CROSS_CITY_VALIDATION_PACKAGE_V1.md"
    )
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(render_cross_city_validation_package_markdown(), encoding="utf-8")
    return target


def _json_pretty(value: Mapping[str, Any]) -> str:
    import json

    return json.dumps(value, indent=2, sort_keys=True, ensure_ascii=True, default=str)


__all__ = [
    "CALLS_ACTUALLY_MADE",
    "CROSS_CITY_VALIDATION_PACKAGE_V1",
    "PHOENIX_REUSE_ACTIVITY_ID",
    "TARGET_LOCAL_TIMESTAMP",
    "build_cross_city_validation_package",
    "render_cross_city_validation_package_markdown",
    "write_cross_city_validation_package_markdown",
]
