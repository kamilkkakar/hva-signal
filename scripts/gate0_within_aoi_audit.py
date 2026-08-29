"""Audit within-AOI TCM structure from existing sanitized + L2 cache fixtures.

No FortyGuard live calls. Does not change frozen night classification.
"""

from __future__ import annotations

import json
import math
from collections import Counter
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
GATE0 = ROOT / "workforce" / "gate0"
OUT = GATE0 / "within_aoi_audit"
AOI_PATH = GATE0 / "track_a" / "aois_preregistered.json"

CONDITIONS = [
    {
        "id": "15:00",
        "stat_key": "average_temperature",
        "sanitized": GATE0 / "track_a" / "raw_sanitized" / "{aoi}.json",
        "cache": GATE0 / "track_a" / "cache",
    },
    {
        "id": "night_min",
        "stat_key": "min_temperature",
        "sanitized": GATE0 / "nighttime" / "raw_sanitized" / "{aoi}_full_day_min.json",
        "cache": GATE0 / "nighttime" / "cache",
    },
    {
        "id": "03:00",
        "stat_key": "average_temperature",
        "sanitized": GATE0 / "nighttime" / "raw_sanitized" / "{aoi}_0300.json",
        "cache": GATE0 / "nighttime" / "cache",
    },
]


def sample_sd(vals: list[float]) -> float | None:
    n = len(vals)
    if n < 2:
        return 0.0 if n == 1 else None
    m = sum(vals) / n
    return math.sqrt(sum((x - m) ** 2 for x in vals) / (n - 1))


def decimal_places(v: Any) -> int | None:
    if v is None:
        return None
    if isinstance(v, int):
        return 0
    s = format(v, ".16g") if isinstance(v, float) else str(v)
    if "e" in s.lower():
        return None
    if "." not in s:
        return 0
    return len(s.split(".", 1)[1].rstrip("0")) or 0


def centroid(geom: dict[str, Any]) -> tuple[float, float] | None:
    coords = (geom or {}).get("coordinates") or []
    if not coords:
        return None
    ring = coords[0]
    xs = [p[0] for p in ring[:-1]]
    ys = [p[1] for p in ring[:-1]]
    if not xs:
        return None
    return (sum(xs) / len(xs), sum(ys) / len(ys))


def load_sanitized(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def load_cache_features(cache_dir: Path, fingerprint: str) -> list[dict[str, Any]] | None:
    p = cache_dir / f"{fingerprint}.json"
    if not p.is_file():
        return None
    doc = json.loads(p.read_text(encoding="utf-8"))
    payload = doc.get("payload") or doc
    result = payload.get("result") or {}
    return list((result.get("map_data") or {}).get("features") or [])


def summarize(features: list[dict[str, Any]], stat_key: str) -> dict[str, Any]:
    raw_vals: list[Any] = []
    floats: list[float] = []
    tile_ids: list[Any] = []
    geoms: list[str] = []
    prop_keys: set[str] = set()
    cents: list[tuple[float, float]] = []
    for f in features:
        props = f.get("properties") or {}
        prop_keys.update(props.keys())
        v = props.get(stat_key)
        raw_vals.append(v)
        if v is not None:
            floats.append(float(v))
        tile_ids.append(props.get("tile_id", f.get("id")))
        geoms.append(json.dumps(f.get("geometry"), sort_keys=True))
        c = centroid(f.get("geometry") or {})
        if c:
            cents.append(c)

    n = len(floats)
    mean = sum(floats) / n if n else None
    sd = sample_sd(floats)
    uniq_exact = sorted({json.dumps(v) for v in raw_vals})
    uniq_float = sorted(set(floats))
    counts = Counter(floats)
    modal, modal_n = counts.most_common(1)[0] if counts else (None, 0)
    places = [decimal_places(v) for v in raw_vals if v is not None]
    types = sorted({type(v).__name__ for v in raw_vals})

    lon_r = lat_r = None
    if n >= 3 and len(set(floats)) > 1 and cents:
        lons = [c[0] for c in cents]
        lats = [c[1] for c in cents]
        lon_r = pearson(lons, floats)
        lat_r = pearson(lats, floats)

    return {
        "tile_count": len(features),
        "tiles_with_stat": n,
        "unique_raw_repr": len(uniq_exact),
        "unique_float": len(uniq_float),
        "unique_raw_values": [json.loads(s) for s in uniq_exact],
        "min": min(floats) if floats else None,
        "max": max(floats) if floats else None,
        "range": (max(floats) - min(floats)) if floats else None,
        "mean": mean,
        "sample_sd": sd,
        "cv": (sd / mean) if sd is not None and mean not in (None, 0) else None,
        "modal_value": modal,
        "modal_count": modal_n,
        "modal_pct": (100.0 * modal_n / n) if n else None,
        "value_frequency": {str(k): v for k, v in counts.most_common()},
        "python_types": types,
        "decimal_places_min": min(places) if places else None,
        "decimal_places_max": max(places) if places else None,
        "unique_tile_ids": len(set(tile_ids)),
        "unique_geometries": len(set(geoms)),
        "property_keys": sorted(prop_keys),
        "all_geometries_identical": len(set(geoms)) == 1,
        "all_tile_ids_identical": len(set(tile_ids)) == 1,
        "literally_identical_before_agg": len(uniq_exact) == 1,
        "pearson_value_vs_lon": lon_r,
        "pearson_value_vs_lat": lat_r,
    }


def pearson(xs: list[float], ys: list[float]) -> float | None:
    n = len(xs)
    if n != len(ys) or n < 3:
        return None
    mx = sum(xs) / n
    my = sum(ys) / n
    num = sum((x - mx) * (y - my) for x, y in zip(xs, ys, strict=True))
    dx = math.sqrt(sum((x - mx) ** 2 for x in xs))
    dy = math.sqrt(sum((y - my) ** 2 for y in ys))
    if dx == 0 or dy == 0:
        return None
    return num / (dx * dy)


def classify_night(row: dict[str, Any]) -> str:
    """Descriptive only. Frozen product bands are not used here."""
    if row["literally_identical_before_agg"] or (row["sample_sd"] or 0) == 0:
        return "EFFECTIVELY CONSTANT"
    rng = row["range"] or 0
    sd = row["sample_sd"] or 0
    if rng >= 0.5 or sd >= 0.15:
        return "STRONG INTERNAL STRUCTURE"
    return "WEAK INTERNAL STRUCTURE"


def main() -> int:
    aois = json.loads(AOI_PATH.read_text(encoding="utf-8"))["aois"]
    OUT.mkdir(parents=True, exist_ok=True)
    rows: list[dict[str, Any]] = []
    sky_detail: dict[str, Any] = {}

    for spec in aois:
        aoi = spec["aoi_id"]
        for cond in CONDITIONS:
            path = Path(str(cond["sanitized"]).format(aoi=aoi))
            doc = load_sanitized(path)
            feats = list(doc["result"]["map_data"]["features"])
            fp = doc["meta"]["fingerprint"]
            cache_feats = load_cache_features(cond["cache"], fp)
            s_sum = summarize(feats, cond["stat_key"])
            c_sum = summarize(cache_feats, cond["stat_key"]) if cache_feats else None
            match = None
            if c_sum:
                match = {
                    "same_tile_count": c_sum["tile_count"] == s_sum["tile_count"],
                    "same_unique_raw": c_sum["unique_raw_repr"] == s_sum["unique_raw_repr"],
                    "same_values": c_sum["unique_raw_values"] == s_sum["unique_raw_values"],
                }
            row = {
                "aoi_id": aoi,
                "urban_form": spec["urban_form"],
                "condition": cond["id"],
                "stat_key": cond["stat_key"],
                "sanitized_path": str(path.relative_to(ROOT)),
                "fingerprint": fp,
                "sanitized": s_sum,
                "cache": c_sum,
                "sanitized_equals_cache_values": match,
            }
            if cond["id"] in ("night_min", "03:00"):
                row["night_structure_class"] = classify_night(s_sum)
            rows.append(row)
            if aoi == "phx_sky_harbor_industrial":
                sky_detail[cond["id"]] = row

    # Cross-AOI precision at 03:00
    precision = []
    for row in rows:
        if row["condition"] != "03:00":
            continue
        s = row["sanitized"]
        precision.append(
            {
                "aoi_id": row["aoi_id"],
                "unique_float": s["unique_float"],
                "decimal_places_min": s["decimal_places_min"],
                "decimal_places_max": s["decimal_places_max"],
                "python_types": s["python_types"],
                "modal_value": s["modal_value"],
                "literally_identical": s["literally_identical_before_agg"],
            }
        )

    sky_times = {
        k: v["sanitized"]["unique_raw_values"] for k, v in sky_detail.items()
    }
    temporally_varying = len({json.dumps(v) for v in sky_times.values()}) > 1
    spatially_constant_each = all(
        v["sanitized"]["literally_identical_before_agg"] for v in sky_detail.values()
    )
    signature = None
    if spatially_constant_each and temporally_varying:
        signature = "TEMPORALLY VARYING / SPATIALLY CONSTANT FIELD"
    elif spatially_constant_each and not temporally_varying:
        signature = "SPATIALLY AND TEMPORALLY CONSTANT FIELD"

    constant_aois_night = []
    for aoi in {r["aoi_id"] for r in rows}:
        night_rows = [r for r in rows if r["aoi_id"] == aoi and r["condition"] in ("night_min", "03:00")]
        if night_rows and all(
            r["sanitized"]["literally_identical_before_agg"] for r in night_rows
        ):
            constant_aois_night.append(aoi)
        elif night_rows and all((r["sanitized"]["sample_sd"] or 0) == 0 for r in night_rows):
            constant_aois_night.append(aoi)

    # Encanto identical-value groups at 03:00
    encanto_groups = None
    encanto_03 = next(
        r for r in rows if r["aoi_id"] == "phx_encanto_park" and r["condition"] == "03:00"
    )
    freq = encanto_03["sanitized"]["value_frequency"]
    encanto_groups = {
        "unique_values": encanto_03["sanitized"]["unique_float"],
        "largest_identical_group": max(int(v) for v in freq.values()) if freq else 0,
        "groups_with_2plus": sum(1 for v in freq.values() if int(v) >= 2),
        "zero_variance_entire_aoi": encanto_03["sanitized"]["literally_identical_before_agg"],
    }

    payload = {
        "gate0_closed": False,
        "no_new_fortyguard_calls": True,
        "does_not_change_frozen_night_classification": True,
        "sky_harbor": {
            "signature": signature,
            "spatially_constant_at_each_time": spatially_constant_each,
            "values_change_across_time": temporally_varying,
            "values_by_time": sky_times,
            "detail": {k: {"sanitized": v["sanitized"], "cache_match": v["sanitized_equals_cache_values"]} for k, v in sky_detail.items()},
        },
        "cross_aoi_03h_precision": precision,
        "constant_aois_at_both_night_conditions": constant_aois_night,
        "option_a_barred_by_two_plus_constant_aois": len(constant_aois_night) >= 2,
        "encanto_03h_identical_groups": encanto_groups,
        "rows": rows,
    }
    OUT.mkdir(parents=True, exist_ok=True)
    (OUT / "AUDIT.json").write_text(json.dumps(payload, indent=2, default=str), encoding="utf-8")
    print("wrote", OUT / "AUDIT.json")
    print("sky signature", signature)
    print("constant night AOIs", constant_aois_night)
    print("option A barred", payload["option_a_barred_by_two_plus_constant_aois"])
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
