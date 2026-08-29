"""Emit combined Track A + nighttime comparison JSON/Markdown. Not a new experiment."""

from __future__ import annotations

import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
GATE0 = ROOT / "workforce" / "gate0"


def main() -> None:
    night = json.loads((GATE0 / "nighttime" / "RESULTS.json").read_text(encoding="utf-8"))
    day = json.loads((GATE0 / "track_a" / "RESULTS.json").read_text(encoding="utf-8"))
    aois = json.loads((GATE0 / "track_a" / "aois_preregistered.json").read_text(encoding="utf-8"))["aois"]

    day_by = {r["aoi_id"]: r for r in day["aois"]}
    min_by = {r["aoi_id"]: r for r in night["daily_night_minimum"]["aois"]}
    h03_by = {r["aoi_id"]: r for r in night["fixed_03h"]["aois"]}

    # 15:00 sample SDs from Track A sanitized average_temperature (n-1), same estimator as night.
    sd15 = {
        "phx_downtown_cbd": 0.004085743613632467,
        "phx_encanto_park": 0.0004177390194570388,
        "phx_sky_harbor_industrial": 0.0,
        "phx_south_mountain_residential": 0.007064370841162286,
        "phx_tempe_mixed": 0.044729158690359,
    }

    rows = []
    for spec in aois:
        i = spec["aoi_id"]
        d, n, h = day_by[i], min_by[i], h03_by[i]
        rows.append(
            {
                "aoi_id": i,
                "label": spec["label"],
                "urban_form": spec["urban_form"],
                "area_km2": spec["area_km2"],
                "tile_count": d["tile_count"],
                "coverage_15": f"{d['tiles_with_mean']}/{d['tile_count']}",
                "coverage_night_min": f"{n['tiles_with_stat']}/{n['tile_count']}",
                "coverage_03": f"{h['tiles_with_stat']}/{h['tile_count']}",
                "completeness": n["completeness"],
                "quality_flags_15": d["quality_flags"],
                "quality_flags_night_min": n["quality_flags"],
                "quality_flags_03": h["quality_flags"],
                "mean_15": d["aoi_mean_tcm_c"],
                "sd_15_sample": sd15[i],
                "mean_night_min": n["aoi_mean_c"],
                "sd_night_min": n["within_aoi_sample_sd_c"],
                "mean_03": h["aoi_mean_c"],
                "sd_03": h["within_aoi_sample_sd_c"],
                "fingerprint_15": d["fingerprint"],
                "fingerprint_night_min": n["fingerprint"],
                "fingerprint_03": h["fingerprint"],
                "sanitized_15": d["sanitized_path"],
                "sanitized_night_min": n["sanitized_path"],
                "sanitized_03": h["sanitized_path"],
                "spatially_constant_all_three": (
                    sd15[i] == 0.0
                    and n["within_aoi_sample_sd_c"] < 1e-12
                    and h["within_aoi_sample_sd_c"] == 0.0
                ),
            }
        )

    wo = [r for r in rows if r["aoi_id"] != "phx_tempe_mixed"]
    payload = {
        "label": "DAY_NIGHT_COMPARISON_FROZEN_PROTOCOL",
        "gate0_closed": False,
        "date": "2024-07-15",
        "granularity_m": 100,
        "aggregation": "AOI-mean of named tile statistic; within-AOI sample SD (n-1)",
        "sd_estimator": "sample standard deviation of tile values (n-1); 15:00 from Track A sanitized average_temperature",
        "DAYTIME_RANGE": night["daytime_between_AOI_spread"],
        "NIGHT_MINIMUM_RANGE": night["night_minimum_between_AOI_spread"],
        "RANGE_03": night["fixed_03h_between_AOI_spread"],
        "daytime_classification": night["daytime_classification"],
        "night_minimum_classification": night["night_minimum_classification"],
        "fixed_03h_classification": night["fixed_03h_classification"],
        "night_minimum_to_daytime_ratio": night["night_minimum_to_daytime_ratio"],
        "fixed_03h_to_daytime_ratio": night["fixed_03h_to_daytime_ratio"],
        "triggered_rule": night["triggered_rule"],
        "rule_a_triggered": False,
        "rule_b_triggered": False,
        "interpretation": "A_DAY_FAILS_BOTH_NIGHT_TESTS_PASS_SAME_BAND",
        "aoi_order_night_warmest_to_coolest": [
            r["aoi_id"] for r in sorted(rows, key=lambda x: -x["mean_night_min"])
        ],
        "aoi_order_03_warmest_to_coolest": [
            r["aoi_id"] for r in sorted(rows, key=lambda x: -x["mean_03"])
        ],
        "aoi_order_15_warmest_to_coolest": [
            r["aoi_id"] for r in sorted(rows, key=lambda x: -x["mean_15"])
        ],
        "night_orders_agree": True,
        "day_order_matches_night": False,
        "diagnostic_only_without_tempe": {
            "note": "Structure description only. Does not change frozen five-AOI classification.",
            "night_minimum_spread": max(r["mean_night_min"] for r in wo)
            - min(r["mean_night_min"] for r in wo),
            "fixed_03h_spread": max(r["mean_03"] for r in wo) - min(r["mean_03"] for r in wo),
        },
        "rows": rows,
    }
    (GATE0 / "nighttime" / "COMPARISON.json").write_text(
        json.dumps(payload, indent=2), encoding="utf-8"
    )


if __name__ == "__main__":
    main()
