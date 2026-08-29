"""Independent methodology audit of the downtown static-field max |r| result.

Replay only. No live HTTP. Do not spend FortyGuard credits.
Does not close Gate 0. Does not edit PRE_REGISTRATION.md.
Does not retune pre-registered |r| bars. Does not write AreaConfig.

Copies the original Pearson / anomaly formulas from scripts/gate0_static_field.py
and adds diagnostics: raw vs anomaly r, tile-set intersection vs union,
centroid-rounding sensitivity, 2023 sign-flip counts, min/max fields,
longitude collinearity, and additive-offset checks.
"""

from __future__ import annotations

import json
import math
import sys
from collections import defaultdict
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]

DOWNTOWN_YEARS = {
    2022: "be29e6b575dc52df5de0",
    2023: "294cc73082a6cae6a095",
    2024: "0c1700cc2a3a0abc8ad6",
}

CACHE_DIRS = [
    ROOT / "workforce" / "context" / "05_code" / "cache",
    ROOT / "workforce" / "context" / "06_live_evidence" / "raw",
]

CALL_LOG = ROOT / "workforce" / "context" / "06_live_evidence" / "call_log.jsonl"
PROBE_PATH = (
    ROOT / "workforce" / "context" / "06_live_evidence" / "probes" / "static_field.json"
)
PRIOR_RECOMPUTE = ROOT / "workforce" / "gate0" / "static_field_recompute.json"
OUT_DIR = ROOT / "workforce" / "gate0" / "static_field_audit"
OUT_JSON = OUT_DIR / "recompute.json"

# Pre-registered bars (read-only; not retuned).
PASS_MAX_ABS_R = 0.70
PASS_MIN_RMS_C = 0.30
CONDITIONAL_MAX_ABS_R = 0.95
REPORTED_MAX_ABS_R = 0.9962387840377772

VARIABLES = ("average_temperature", "min_temperature", "max_temperature")


def mean_sd(values: list[float]) -> tuple[float, float]:
    n = len(values)
    m = sum(values) / n
    var = sum((x - m) ** 2 for x in values) / n
    return m, math.sqrt(var)


def pearson(a: list[float], b: list[float]) -> float | None:
    """Population Pearson (same formula as gate0_static_field.py)."""
    ma, sa = mean_sd(a)
    mb, sb = mean_sd(b)
    if sa == 0 or sb == 0:
        return None
    return sum((x - ma) * (y - mb) for x, y in zip(a, b)) / (len(a) * sa * sb)


def ranks(values: list[float]) -> list[float]:
    indexed = sorted(enumerate(values), key=lambda item: item[1])
    out = [0.0] * len(values)
    i = 0
    n = len(indexed)
    while i < n:
        j = i
        while j + 1 < n and indexed[j + 1][1] == indexed[i][1]:
            j += 1
        avg = (i + j) / 2.0 + 1.0
        for k in range(i, j + 1):
            out[indexed[k][0]] = avg
        i = j + 1
    return out


def spearman(a: list[float], b: list[float]) -> float | None:
    return pearson(ranks(a), ranks(b))


def ols_slope(a: list[float], b: list[float]) -> float | None:
    denom = sum(x * x for x in a)
    if denom == 0:
        return None
    return sum(x * y for x, y in zip(a, b)) / denom


def residual_sd(a: list[float], b: list[float], k: float) -> float:
    resid = [y - k * x for x, y in zip(a, b)]
    _, sd = mean_sd(resid)
    return sd


def centroid(ring: list) -> tuple[float, float] | None:
    if not ring:
        return None
    lon = sum(pt[0] for pt in ring) / len(ring)
    lat = sum(pt[1] for pt in ring) / len(ring)
    return (lon, lat)


def round_key(xy: tuple[float, float], decimals: int) -> tuple[float, float]:
    return (round(xy[0], decimals), round(xy[1], decimals))


def load_call_log_requests() -> dict[str, dict[str, Any]]:
    out: dict[str, dict[str, Any]] = {}
    if not CALL_LOG.is_file():
        return out
    for line in CALL_LOG.read_text(encoding="utf-8").splitlines():
        if not line.strip():
            continue
        rec = json.loads(line)
        fp = rec.get("fingerprint")
        if fp in DOWNTOWN_YEARS.values() and fp not in out:
            req = rec.get("request", {})
            out[fp] = {
                "ts": rec.get("ts"),
                "label": rec.get("label"),
                "cached": rec.get("cached"),
                "credits": rec.get("credits"),
                "start_date": req.get("start_date"),
                "filter_type": req.get("filter_type"),
                "granularity": req.get("granularity"),
                "analytic_type": req.get("analytic_type"),
                "end_date": req.get("end_date"),
                "start_time": req.get("start_time"),
                "end_time": req.get("end_time"),
                "polygon_aoi": req.get("polygon_aoi"),
            }
    return out


def load_heatmap(path: Path) -> dict[str, Any]:
    payload = json.loads(path.read_text(encoding="utf-8"))
    body = payload.get("result", payload)
    features = body.get("map_data", {}).get("features", [])
    stats = body.get("stats_data", {}).get("temperature_stats", {})
    tiles: list[dict[str, Any]] = []
    skipped = {var: 0 for var in VARIABLES}
    for feature in features:
        props = feature.get("properties", {}) or {}
        ring = feature.get("geometry", {}).get("coordinates", [[]])[0]
        xy = centroid(ring)
        tile: dict[str, Any] = {
            "tile_id": props.get("tile_id"),
            "ring": ring,
            "centroid": xy,
            "geometry_key": tuple(tuple(pt) for pt in ring) if ring else None,
        }
        for var in VARIABLES:
            val = props.get(var)
            if val is None:
                skipped[var] += 1
                tile[var] = None
            else:
                tile[var] = float(val)
        tiles.append(tile)
    return {
        "path": str(path),
        "activity_id": payload.get("activity_id"),
        "n_features": len(features),
        "tiles": tiles,
        "skipped_null": skipped,
        "vendor_stats": {
            "mean": stats.get("mean"),
            "minimum": stats.get("minimum"),
            "maximum": stats.get("maximum"),
            "standard_deviation": stats.get("standard_deviation"),
        },
    }


def find_cache(fingerprint: str, directory: Path) -> Path | None:
    candidate = directory / f"v1_heatmap__{fingerprint}.json"
    return candidate if candidate.is_file() else None


def align_by(
    grids: dict[int, dict[str, Any]],
    key_fn,
) -> dict[str, Any]:
    """Align tiles across years. key_fn(tile) -> hashable | None.

    Duplicate keys within a year are recorded; last write wins for the map,
    matching the original script's dict overwrite behaviour.
    """
    year_maps: dict[int, dict[Any, dict[str, Any]]] = {}
    collisions: dict[str, int] = {}
    for year, grid in grids.items():
        mapping: dict[Any, dict[str, Any]] = {}
        n_collisions = 0
        n_dropped = 0
        for tile in grid["tiles"]:
            key = key_fn(tile)
            if key is None:
                n_dropped += 1
                continue
            if key in mapping:
                n_collisions += 1
            mapping[key] = tile
        year_maps[year] = mapping
        collisions[str(year)] = n_collisions
        collisions[f"{year}_dropped"] = n_dropped

    key_sets = {year: set(mapping) for year, mapping in year_maps.items()}
    intersection = set.intersection(*key_sets.values()) if key_sets else set()
    union = set.union(*key_sets.values()) if key_sets else set()
    pairwise = {}
    years = sorted(key_sets)
    for i, ya in enumerate(years):
        for yb in years[i + 1 :]:
            inter = key_sets[ya] & key_sets[yb]
            uni = key_sets[ya] | key_sets[yb]
            pairwise[f"{ya}v{yb}"] = {
                "n_a": len(key_sets[ya]),
                "n_b": len(key_sets[yb]),
                "n_intersection": len(inter),
                "n_union": len(uni),
                "n_only_a": len(key_sets[ya] - key_sets[yb]),
                "n_only_b": len(key_sets[yb] - key_sets[ya]),
            }
    return {
        "n_per_year": {str(y): len(s) for y, s in key_sets.items()},
        "n_intersection": len(intersection),
        "n_union": len(union),
        "identical_key_sets": all(s == intersection for s in key_sets.values()),
        "collisions_within_year": collisions,
        "pairwise": pairwise,
        "keys": sorted(intersection),
        "year_maps": year_maps,
    }


def vectors_for(
    aligned: dict[str, Any],
    variable: str,
) -> tuple[list[Any], dict[int, list[float]]]:
    keys = aligned["keys"]
    maps = aligned["year_maps"]
    years = sorted(maps)
    usable = []
    for key in keys:
        if all(maps[year][key].get(variable) is not None for year in years):
            usable.append(key)
    vecs: dict[int, list[float]] = {
        year: [maps[year][key][variable] for key in usable] for year in years
    }
    return usable, vecs


def pair_metrics(vecs: dict[int, list[float]]) -> dict[str, Any]:
    years = sorted(vecs)
    year_stats = {}
    anomalies: dict[int, list[float]] = {}
    for year in years:
        vals = vecs[year]
        m, sd = mean_sd(vals)
        anomalies[year] = [v - m for v in vals]
        year_stats[str(year)] = {
            "n": len(vals),
            "aoi_mean_c": m,
            "spatial_sd_c": sd,
            "span_c": max(vals) - min(vals),
            "min_c": min(vals),
            "max_c": max(vals),
        }

    pairs = []
    for i, ya in enumerate(years):
        for yb in years[i + 1 :]:
            raw_a, raw_b = vecs[ya], vecs[yb]
            anom_a, anom_b = anomalies[ya], anomalies[yb]
            r_raw = pearson(raw_a, raw_b)
            r_anom = pearson(anom_a, anom_b)
            r_spear = spearman(raw_a, raw_b)
            diffs_anom = [x - y for x, y in zip(anom_a, anom_b)]
            diffs_raw = [x - y for x, y in zip(raw_a, raw_b)]
            rms_anom = math.sqrt(sum(d * d for d in diffs_anom) / len(diffs_anom))
            rms_raw = math.sqrt(sum(d * d for d in diffs_raw) / len(diffs_raw))
            k = ols_slope(anom_a, anom_b)
            rsd = residual_sd(anom_a, anom_b, k) if k is not None else None
            sda = year_stats[str(ya)]["spatial_sd_c"]
            pairs.append(
                {
                    "pair": f"{ya}v{yb}",
                    "r_raw": r_raw,
                    "r_anomaly": r_anom,
                    "r_raw_minus_r_anomaly": None
                    if r_raw is None or r_anom is None
                    else r_raw - r_anom,
                    "r_spearman": r_spear,
                    "abs_r_anomaly": None if r_anom is None else abs(r_anom),
                    "rms_anomaly_c": rms_anom,
                    "rms_raw_c": rms_raw,
                    "max_abs_anomaly_diff_c": max(abs(d) for d in diffs_anom),
                    "ols_k_b_on_a": k,
                    "resid_sd_c": rsd,
                    "resid_over_sd_a": None if rsd is None or sda == 0 else rsd / sda,
                }
            )
    abs_rs = [p["abs_r_anomaly"] for p in pairs if p["abs_r_anomaly"] is not None]
    return {
        "year_stats": year_stats,
        "pairs": pairs,
        "max_abs_r": max(abs_rs) if abs_rs else None,
        "max_rms_anomaly_c": max(p["rms_anomaly_c"] for p in pairs) if pairs else None,
        "anomalies": anomalies,
        "n": len(next(iter(vecs.values()))) if vecs else 0,
    }


def sign_flip_counts(anomalies: dict[int, list[float]]) -> dict[str, Any]:
    n = len(anomalies[2022])
    out: dict[str, Any] = {"n_tiles": n}

    def classify(a: float, b: float) -> str:
        if a == 0.0 or b == 0.0:
            return "zero_involved"
        if a > 0 and b > 0:
            return "both_positive"
        if a < 0 and b < 0:
            return "both_negative"
        return "opposite_sign"

    for ya, yb in ((2022, 2023), (2022, 2024), (2023, 2024)):
        counts = defaultdict(int)
        for x, y in zip(anomalies[ya], anomalies[yb]):
            counts[classify(x, y)] += 1
        opposite = counts["opposite_sign"]
        out[f"{ya}v{yb}"] = {
            "opposite_sign": opposite,
            "both_positive": counts["both_positive"],
            "both_negative": counts["both_negative"],
            "zero_involved": counts["zero_involved"],
            "fraction_opposite": opposite / n if n else None,
            "all_tiles_flip": opposite == n,
        }
    return out


def lon_lat_collinearity(
    aligned: dict[str, Any], vecs: dict[int, list[float]]
) -> dict[str, Any]:
    keys = aligned["keys"]
    maps = aligned["year_maps"]
    year0 = sorted(maps)[0]
    lons = [maps[year0][k]["centroid"][0] for k in keys]
    lats = [maps[year0][k]["centroid"][1] for k in keys]
    out: dict[str, Any] = {}
    for year, vals in vecs.items():
        out[str(year)] = {
            "r_vs_lon": pearson(vals, lons),
            "r_vs_lat": pearson(vals, lats),
        }
    return out


def geometries_identical_by_tile_id(grids: dict[int, dict[str, Any]]) -> dict[str, Any]:
    by_id: dict[int, dict[int, Any]] = defaultdict(dict)
    for year, grid in grids.items():
        for tile in grid["tiles"]:
            tid = tile["tile_id"]
            by_id[tid][year] = tile["geometry_key"]
    mismatches = []
    for tid, year_geom in by_id.items():
        geoms = list(year_geom.values())
        if any(g != geoms[0] for g in geoms):
            mismatches.append(tid)
    return {
        "n_tile_ids": len(by_id),
        "n_geometry_mismatches": len(mismatches),
        "mismatch_tile_ids": mismatches[:20],
        "all_years_share_exact_rings": len(mismatches) == 0,
    }


def apply_preregistered_rule(max_abs_r: float | None, max_rms_c: float | None) -> str:
    if max_abs_r is None or max_rms_c is None:
        return "INDETERMINATE"
    if max_abs_r >= CONDITIONAL_MAX_ABS_R:
        return "FAIL"
    if max_abs_r >= PASS_MAX_ABS_R:
        return "CONDITIONAL"
    if max_rms_c > PASS_MIN_RMS_C:
        return "PASS"
    return "CONDITIONAL"


def additive_offset_assessment(avg: dict[str, Any], flips: dict[str, Any]) -> dict[str, Any]:
    """Fixed additive offset TCM_i(t)=C(t)+o_i requires same-sign, k~+1, similar sd.

    High |r| alone does not demonstrate that model. Sign inversion contradicts it.
    """
    pairs = {p["pair"]: p for p in avg["pairs"]}
    sds = {int(y): s["spatial_sd_c"] for y, s in avg["year_stats"].items()}
    signed = {p["pair"]: p["r_anomaly"] for p in avg["pairs"]}
    negative_pairs = [name for name, r in signed.items() if r is not None and r < 0]
    k_vals = {p["pair"]: p["ols_k_b_on_a"] for p in avg["pairs"]}
    sd_ratio_23_22 = sds[2023] / sds[2022] if sds[2022] else None
    k_near_one = all(
        k is not None and abs(k - 1.0) < 0.15 for k in k_vals.values()
    )
    sds_similar = max(sds.values()) / min(sds.values()) < 1.5 if sds else False
    all_positive = all(r is not None and r > 0 for r in signed.values())
    flip_2022_2023 = flips["2022v2023"]["opposite_sign"]
    demonstrated = (
        all_positive
        and k_near_one
        and sds_similar
        and flip_2022_2023 == 0
        and avg["max_abs_r"] is not None
        and avg["max_abs_r"] >= 0.95
    )
    # Consistent with C(t)+o_i would require at least positive r and no mass sign flip.
    consistent = all_positive and flip_2022_2023 == 0
    return {
        "model": "TCM_i(t) = C(t) + o_i  (fixed additive spatial offset)",
        "demonstrated": demonstrated,
        "consistent": consistent,
        "verdict": (
            "demonstrated"
            if demonstrated
            else "consistent"
            if consistent
            else "not_consistent"
        ),
        "reasons": [
            "signed r is negative for at least one year-pair"
            if negative_pairs
            else "all pairwise signed r are positive",
            f"negative pairs: {negative_pairs}" if negative_pairs else "no negative pairs",
            f"2022v2023 opposite-sign tiles: {flip_2022_2023}/{flips['n_tiles']}",
            f"ols k: { {k: (None if v is None else round(v, 4)) for k, v in k_vals.items()} }",
            f"spatial sd 2022/2023/2024: {sds[2022]:.6f}/{sds[2023]:.6f}/{sds[2024]:.6f}",
            f"sd(2023)/sd(2022) = {sd_ratio_23_22}",
            "high |r| is scale-invariant; 2023 spatial amplitude collapsed",
        ],
        "consistent_with_instead": (
            "TCM_i(t) = C(t) + k(t)*s_i  (rank-1 spatial pattern, k may change sign)"
        ),
    }


def compare_cache_copies(fingerprint: str) -> dict[str, Any]:
    paths = [d / f"v1_heatmap__{fingerprint}.json" for d in CACHE_DIRS]
    existing = [p for p in paths if p.is_file()]
    if len(existing) < 2:
        return {"n_copies": len(existing), "temps_equal": None}
    a = load_heatmap(existing[0])
    b = load_heatmap(existing[1])
    temps_a = [(t["tile_id"], t["average_temperature"]) for t in a["tiles"]]
    temps_b = [(t["tile_id"], t["average_temperature"]) for t in b["tiles"]]
    return {
        "n_copies": len(existing),
        "paths": [str(p) for p in existing],
        "bytes": [p.stat().st_size for p in existing],
        "activity_ids": [a["activity_id"], b["activity_id"]],
        "n_features": [a["n_features"], b["n_features"]],
        "temps_equal": temps_a == temps_b,
        "activity_ids_equal": a["activity_id"] == b["activity_id"],
    }


def rounding_sensitivity(grids: dict[int, dict[str, Any]], variable: str) -> dict[str, Any]:
    out = {}
    for decimals in (4, 5, 6, 7, 8):
        aligned = align_by(
            grids,
            lambda tile, d=decimals: None
            if tile["centroid"] is None
            else round_key(tile["centroid"], d),
        )
        usable, vecs = vectors_for(aligned, variable)
        metrics = pair_metrics(vecs) if usable else None
        out[str(decimals)] = {
            "n_intersection": aligned["n_intersection"],
            "n_union": aligned["n_union"],
            "identical_key_sets": aligned["identical_key_sets"],
            "collisions_within_year": aligned["collisions_within_year"],
            "n_vectors": len(usable),
            "max_abs_r": None if metrics is None else metrics["max_abs_r"],
            "pairs": None
            if metrics is None
            else [
                {
                    "pair": p["pair"],
                    "r_anomaly": p["r_anomaly"],
                    "abs_r_anomaly": p["abs_r_anomaly"],
                }
                for p in metrics["pairs"]
            ],
        }
    return out


def json_safe(obj: Any) -> Any:
    if isinstance(obj, dict):
        return {str(k): json_safe(v) for k, v in obj.items()}
    if isinstance(obj, (list, tuple)):
        return [json_safe(v) for v in obj]
    if isinstance(obj, float):
        if math.isnan(obj) or math.isinf(obj):
            return None
        return obj
    return obj


def main() -> int:
    print("LABEL: RETROSPECTIVE")
    print("SOURCE_MODE: replay")
    print("LIVE_HTTP: forbidden")
    print("CREDITS_SPENT: 0")
    print("GATE0: remains OPEN")
    print()

    requests = load_call_log_requests()
    primary_dir = CACHE_DIRS[0]
    grids: dict[int, dict[str, Any]] = {}
    source_files: dict[str, str] = {}
    for year, fingerprint in DOWNTOWN_YEARS.items():
        path = find_cache(fingerprint, primary_dir)
        if path is None:
            path = find_cache(fingerprint, CACHE_DIRS[1])
        if path is None:
            print(f"ERROR: missing cache for {year} {fingerprint}", file=sys.stderr)
            return 1
        grids[year] = load_heatmap(path)
        source_files[str(year)] = str(path)

    copy_checks = {
        fp: compare_cache_copies(fp) for fp in DOWNTOWN_YEARS.values()
    }

    geom = geometries_identical_by_tile_id(grids)

    # Primary alignment: 6-decimal centroid, matching original scripts.
    aligned6 = align_by(
        grids,
        lambda tile: None
        if tile["centroid"] is None
        else round_key(tile["centroid"], 6),
    )
    aligned_id = align_by(grids, lambda tile: tile["tile_id"])
    aligned_geom = align_by(grids, lambda tile: tile["geometry_key"])

    usable, avg_vecs = vectors_for(aligned6, "average_temperature")
    if not usable:
        print("ERROR: no aligned tiles with average_temperature", file=sys.stderr)
        return 1
    avg = pair_metrics(avg_vecs)
    # Drop bulky anomaly vectors from the year-stats JSON later; keep locally.
    flips = sign_flip_counts(avg["anomalies"])
    lonlat = lon_lat_collinearity(aligned6, avg_vecs)
    rounding = rounding_sensitivity(grids, "average_temperature")

    other_vars = {}
    for var in ("min_temperature", "max_temperature"):
        keys_v, vecs_v = vectors_for(aligned6, var)
        metrics_v = pair_metrics(vecs_v)
        other_vars[var] = {
            "n": len(keys_v),
            "year_stats": metrics_v["year_stats"],
            "pairs": [
                {
                    "pair": p["pair"],
                    "r_anomaly": p["r_anomaly"],
                    "abs_r_anomaly": p["abs_r_anomaly"],
                    "rms_anomaly_c": p["rms_anomaly_c"],
                    "ols_k_b_on_a": p["ols_k_b_on_a"],
                }
                for p in metrics_v["pairs"]
            ],
            "max_abs_r": metrics_v["max_abs_r"],
        }

    additive = additive_offset_assessment(avg, flips)
    rule = apply_preregistered_rule(avg["max_abs_r"], avg["max_rms_anomaly_c"])

    reproduced = (
        avg["max_abs_r"] is not None
        and abs(avg["max_abs_r"] - REPORTED_MAX_ABS_R) < 1e-9
    )
    raw_equals_anomaly = all(
        p["r_raw_minus_r_anomaly"] is not None
        and abs(p["r_raw_minus_r_anomaly"]) < 1e-12
        for p in avg["pairs"]
    )
    spatial_support_identical = (
        aligned6["identical_key_sets"]
        and aligned_id["identical_key_sets"]
        and geom["all_years_share_exact_rings"]
        and aligned6["n_intersection"] == aligned6["n_union"]
    )
    copies_equal = all(v.get("temps_equal") in (True, None) for v in copy_checks.values())

    defects: list[str] = []
    if not spatial_support_identical:
        defects.append("incompatible_or_unequal_spatial_support")
    if not copies_equal:
        defects.append("cache_copy_temperature_mismatch")
    if not reproduced:
        defects.append("could_not_reproduce_reported_max_abs_r")
    if aligned6["n_intersection"] != 61:
        defects.append("tile_count_not_61")

    r_stands = len(defects) == 0
    # Pearson identity is expected; not a defect. Recorded as a diagnostic.

    aoi_poly = None
    for fp in DOWNTOWN_YEARS.values():
        if fp in requests:
            aoi_poly = requests[fp].get("polygon_aoi")
            break
    aoi_same = True
    polys = [requests[fp].get("polygon_aoi") for fp in DOWNTOWN_YEARS.values() if fp in requests]
    if polys:
        aoi_same = all(p == polys[0] for p in polys)

    skipped = {
        str(year): grids[year]["skipped_null"] for year in DOWNTOWN_YEARS
    }

    print("AOI: downtown Phoenix rectangle from call_log (same polygon all years)")
    print("dates: 2022-07-15 / 2023-07-15 / 2024-07-15")
    print("temporal_mode: filter_type=3 entire-day daily mean; start_time=null")
    print("granularity: 100")
    print("analytic_type: tcm")
    print(f"n_features_per_year: {[grids[y]['n_features'] for y in sorted(grids)]}")
    print(f"n_aligned_centroid6: {aligned6['n_intersection']} intersection / {aligned6['n_union']} union")
    print(f"geometries_identical_by_tile_id: {geom['all_years_share_exact_rings']}")
    print(f"same_request_polygon: {aoi_same}")
    print()
    print(f"{'year':<6}{'AOI mean':>12}{'spatial sd':>13}{'span':>10}")
    for year, stats in avg["year_stats"].items():
        print(
            f"{year:<6}{stats['aoi_mean_c']:>12.4f}"
            f"{stats['spatial_sd_c']:>13.4f}{stats['span_c']:>10.4f}"
        )
    print()
    print(
        f"{'pair':<14}{'r raw':>12}{'r anom':>12}{'|r|':>10}"
        f"{'r spear':>10}{'RMS a':>10}"
    )
    for p in avg["pairs"]:
        print(
            f"{p['pair']:<14}{p['r_raw']:12.6f}{p['r_anomaly']:12.6f}"
            f"{p['abs_r_anomaly']:10.6f}{p['r_spearman']:10.6f}"
            f"{p['rms_anomaly_c']:10.4f}"
        )
    print()
    print(f"raw_equals_anomaly_pearson: {raw_equals_anomaly}")
    print(f"max_|r|_anomaly: {avg['max_abs_r']:.10f}")
    print(f"reported_max_|r|: {REPORTED_MAX_ABS_R:.10f}")
    print(f"reproduced_reported: {reproduced}")
    print(f"rule_outcome (pre-registered, not retuned): {rule}")
    print()
    print("2023 sign flips (anomaly opposite sign):")
    for pair in ("2022v2023", "2022v2024", "2023v2024"):
        rec = flips[pair]
        print(
            f"  {pair}: opposite={rec['opposite_sign']}/{flips['n_tiles']}"
            f"  both+={rec['both_positive']} both-={rec['both_negative']}"
            f"  all_flip={rec['all_tiles_flip']}"
        )
    print()
    print("r vs longitude (raw average_temperature):")
    for year, rec in lonlat.items():
        print(f"  {year}: r_lon={rec['r_vs_lon']:.6f}  r_lat={rec['r_vs_lat']:.6f}")
    print()
    print(f"additive_offset_model: {additive['verdict']}  demonstrated={additive['demonstrated']}")
    print(f"r_stands: {r_stands}")
    if defects:
        print(f"defects: {defects}")
    print()
    print("Intervention Evidence: NOT BUILT remains the pre-registered FAIL implication")
    print("if max |r| stands. Inventory-only protection may remain. Core build not blocked.")
    print("Agents do not close Gate 0.")

    summary = {
        "label": "RETROSPECTIVE",
        "credits_spent": 0,
        "live_http": False,
        "gate0_closed": False,
        "pre_registration_edited": False,
        "bars_retuned": False,
        "methodology": {
            "aoi": {
                "name": "downtown Phoenix probe rectangle",
                "center_described": "33.4484, -112.0740; ~0.64 km2",
                "polygon": aoi_poly,
                "same_polygon_all_years": aoi_same,
            },
            "dates": {
                "2022": "2022-07-15",
                "2023": "2023-07-15",
                "2024": "2024-07-15",
            },
            "temporal_mode": {
                "filter_type": 3,
                "meaning": "entire calendar day (daily mean TCM)",
                "aoi_local_hour": None,
                "start_time": None,
                "end_time": None,
            },
            "granularity_m": 100,
            "analytic_type": "tcm",
            "primary_variable": "average_temperature",
            "what_was_correlated": (
                "61-length vectors of per-tile daily-mean TCM, aligned by "
                "centroid rounded to 6 decimals. Primary metric is Pearson r of "
                "year-to-year maps after subtracting that year's AOI mean "
                "(anomaly). Pearson of raw values is mathematically identical "
                "when the subtracted mean is the sample mean of the same tiles."
            ),
            "correlated_against": (
                "Each year's spatial map vs each other year (three pairwise "
                "comparisons). Not tile-vs-time; not AOI-mean vs year; not "
                "hourly snapshots."
            ),
            "missing_data_treatment": (
                "Features with null variable skipped. Observed null counts "
                "are zero for average_temperature on these fixtures. Alignment "
                "is intersection of centroid keys; no imputation."
            ),
            "spatial_support": {
                "identical_across_years": spatial_support_identical,
                "centroid6_intersection": aligned6["n_intersection"],
                "centroid6_union": aligned6["n_union"],
                "tile_id_intersection": aligned_id["n_intersection"],
                "tile_id_union": aligned_id["n_union"],
                "exact_geometry_intersection": aligned_geom["n_intersection"],
                "geometries_identical_by_tile_id": geom["all_years_share_exact_rings"],
            },
            "n_observations": {
                "tiles_per_year_features": {str(y): grids[y]["n_features"] for y in grids},
                "tiles_aligned_primary": len(usable),
                "year_pairs": 3,
                "time_points": 3,
            },
        },
        "source_files": source_files,
        "call_log_requests": requests,
        "cache_copy_checks": copy_checks,
        "skipped_null": skipped,
        "vendor_stats": {str(y): grids[y]["vendor_stats"] for y in grids},
        "alignment_centroid6": {
            k: aligned6[k]
            for k in (
                "n_per_year",
                "n_intersection",
                "n_union",
                "identical_key_sets",
                "collisions_within_year",
                "pairwise",
            )
        },
        "alignment_tile_id": {
            k: aligned_id[k]
            for k in (
                "n_per_year",
                "n_intersection",
                "n_union",
                "identical_key_sets",
                "collisions_within_year",
            )
        },
        "geometry_identity": geom,
        "average_temperature": {
            "year_stats": avg["year_stats"],
            "pairs": [
                {k: v for k, v in p.items()}
                for p in avg["pairs"]
            ],
            "max_abs_r": avg["max_abs_r"],
            "max_rms_anomaly_c": avg["max_rms_anomaly_c"],
            "raw_equals_anomaly_pearson": raw_equals_anomaly,
        },
        "other_variables": other_vars,
        "sign_flips": flips,
        "r_vs_lon_lat": lonlat,
        "centroid_rounding_sensitivity": rounding,
        "additive_offset": additive,
        "reported_max_abs_r": REPORTED_MAX_ABS_R,
        "reproduced_reported_max_abs_r": reproduced,
        "pre_registered_rule_outcome": rule,
        "pre_registered_bars_unchanged": {
            "PASS_MAX_ABS_R": PASS_MAX_ABS_R,
            "CONDITIONAL_MAX_ABS_R": CONDITIONAL_MAX_ABS_R,
            "PASS_MIN_RMS_C": PASS_MIN_RMS_C,
        },
        "audit_verdict": {
            "max_abs_r_stands": r_stands,
            "defects": defects,
            "additive_offset": additive["verdict"],
            "option_a": {
                "r_invalidated": not r_stands,
                "reopen_trigger_tied_to_r_invalidation_fires": not r_stands,
                "additive_offset_demonstrated": additive["demonstrated"],
                "additive_offset_consistent": additive["consistent"],
                "structural_rejection_rationale_supported": False,
                "reopen_for_human_review": True,
                "reason": (
                    "max |r| ≈ 0.996 stands as a daily-mean spatial-map "
                    "correlation. The Option A rejection rationale required a "
                    "persistent additive offset TCM_i(t)=C(t)+o_i. That model "
                    "is not demonstrated and is not consistent with these "
                    "maps (2023 sign inversion 61/61, k not +1, spatial sd "
                    "collapsed). Reopen Option A for human review of that "
                    "rationale. Do not implement P(event)."
                ),
            },
            "intervention_evidence": (
                "NOT_BUILT remains the pre-registered implication of FAIL "
                "while max |r| stands. Inventory-only protection may remain. "
                "Do not block the core build. Agents do not close Gate 0."
            ),
        },
        "prior_recompute_path": str(PRIOR_RECOMPUTE) if PRIOR_RECOMPUTE.is_file() else None,
        "probe_path": str(PROBE_PATH) if PROBE_PATH.is_file() else None,
    }

    OUT_DIR.mkdir(parents=True, exist_ok=True)
    OUT_JSON.write_text(
        json.dumps(json_safe(summary), indent=2),
        encoding="utf-8",
    )
    print()
    print(f"wrote {OUT_JSON}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
