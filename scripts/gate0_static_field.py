"""Gate 0 temporal/static-field helper against existing downtown year fixtures.

Replay only. No live HTTP. Do not spend FortyGuard credits.
Applies pre-registered rules from workforce/gate0/PRE_REGISTRATION.md.
Labels the application RETROSPECTIVE (fixtures collected before this session).
Does not close Gate 0.
"""

from __future__ import annotations

import argparse
import json
import math
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]

DOWNTOWN_YEARS = {
    2022: "be29e6b575dc52df5de0",
    2023: "294cc73082a6cae6a095",
    2024: "0c1700cc2a3a0abc8ad6",
}

CACHE_DIRS = [
    ROOT / "workforce" / "context" / "05_code" / "cache",
    ROOT / "workforce" / "context" / "06_live_evidence" / "raw",
    ROOT / "apps" / "api" / "tests" / "fixtures" / "fortyguard",
]

PROBE_PATH = (
    ROOT / "workforce" / "context" / "06_live_evidence" / "probes" / "static_field.json"
)

# Pre-registered (PRE_REGISTRATION.md §2). Do not retune after seeing results.
PASS_MAX_ABS_R = 0.70
PASS_MIN_RMS_C = 0.30
CONDITIONAL_MAX_ABS_R = 0.95


def _centroid_key(ring: list) -> tuple[float, float] | None:
    if not ring:
        return None
    lon = sum(pt[0] for pt in ring) / len(ring)
    lat = sum(pt[1] for pt in ring) / len(ring)
    return (round(lon, 6), round(lat, 6))


def load_tiles_from_cache(cache_file: Path) -> dict[tuple[float, float], float]:
    payload = json.loads(cache_file.read_text(encoding="utf-8"))
    body = payload.get("result", payload)
    out: dict[tuple[float, float], float] = {}
    for feature in body.get("map_data", {}).get("features", []):
        props = feature.get("properties", {})
        temp = props.get("average_temperature")
        if temp is None:
            continue
        ring = feature.get("geometry", {}).get("coordinates", [[]])[0]
        key = _centroid_key(ring)
        if key is None:
            continue
        out[key] = float(temp)
    return out


def find_cache_file(fingerprint: str) -> Path | None:
    name = f"v1_heatmap__{fingerprint}.json"
    for directory in CACHE_DIRS:
        candidate = directory / name
        if candidate.is_file():
            return candidate
    return None


def load_grids_from_cache() -> tuple[dict[int, dict], Path | None]:
    grids: dict[int, dict] = {}
    source: Path | None = None
    for year, fingerprint in DOWNTOWN_YEARS.items():
        path = find_cache_file(fingerprint)
        if path is None:
            return {}, None
        tiles = load_tiles_from_cache(path)
        if not tiles:
            return {}, None
        grids[year] = tiles
        source = path.parent
    return grids, source


def load_grids_from_probe(path: Path) -> dict[int, dict]:
    data = json.loads(path.read_text(encoding="utf-8"))
    grids: dict[int, dict] = {2022: {}, 2023: {}, 2024: {}}
    for tile in data.get("tiles", []):
        key = (round(float(tile["lon"]), 6), round(float(tile["lat"]), 6))
        grids[2022][key] = float(tile["t2022"])
        grids[2023][key] = float(tile["t2023"])
        grids[2024][key] = float(tile["t2024"])
    return grids


def mean_sd(values: list[float]) -> tuple[float, float]:
    n = len(values)
    m = sum(values) / n
    var = sum((x - m) ** 2 for x in values) / n
    return m, math.sqrt(var)


def pearson(a: list[float], b: list[float]) -> float | None:
    ma, sa = mean_sd(a)
    mb, sb = mean_sd(b)
    if sa == 0 or sb == 0:
        return None
    return sum((x - ma) * (y - mb) for x, y in zip(a, b)) / (len(a) * sa * sb)


def apply_preregistered_rule(max_abs_r: float, max_rms_c: float) -> str:
    if max_abs_r >= CONDITIONAL_MAX_ABS_R:
        return "FAIL"
    if max_abs_r >= PASS_MAX_ABS_R:
        return "CONDITIONAL"
    if max_rms_c > PASS_MIN_RMS_C:
        return "PASS"
    return "CONDITIONAL"


def main() -> int:
    parser = argparse.ArgumentParser(description="Gate 0 static-field recompute (replay only).")
    parser.add_argument(
        "--probe",
        type=Path,
        default=PROBE_PATH,
        help="Fallback probes/static_field.json if downtown cache files are missing.",
    )
    args = parser.parse_args()

    print("LABEL: RETROSPECTIVE")
    print("SOURCE_MODE: replay")
    print("LIVE_HTTP: forbidden")
    print("CREDITS_SPENT: 0")
    print()

    grids, cache_dir = load_grids_from_cache()
    source_kind = "downtown_cache"
    source_path: Path | str
    if grids:
        source_path = cache_dir  # type: ignore[assignment]
        print(f"input: downtown heatmap caches under {cache_dir}")
    else:
        if not args.probe.is_file():
            print("ERROR: no downtown cache files and no probe JSON.", file=sys.stderr)
            return 1
        grids = load_grids_from_probe(args.probe)
        source_kind = "probe_json"
        source_path = args.probe
        print(f"input: probe JSON {args.probe} (cache files not found)")

    keys = set.intersection(*(set(g) for g in grids.values()))
    if not keys:
        print("ERROR: no tiles align across years.", file=sys.stderr)
        return 1
    keys = sorted(keys)
    years = sorted(grids)

    print(f"aoi: downtown Phoenix (same AOI, day-of-year 15 July, granularity 100, filter_type=3 tcm)")
    print(f"n_tiles_aligned: {len(keys)}")
    print(f"years: {years}")
    print(f"source_kind: {source_kind}")
    print()
    print(f"{'year':<6}{'AOI mean':>12}{'spatial sd':>13}{'span':>10}")

    anomalies: dict[int, list[float]] = {}
    year_stats = {}
    for year in years:
        vals = [grids[year][k] for k in keys]
        m, sd = mean_sd(vals)
        anomalies[year] = [v - m for v in vals]
        year_stats[year] = {"aoi_mean_c": m, "spatial_sd_c": sd, "span_c": max(vals) - min(vals)}
        print(f"{year:<6}{m:>12.4f}{sd:>13.4f}{max(vals) - min(vals):>10.4f}")

    print()
    print(f"{'pair':<14}{'r signed':>12}{'|r|':>10}{'RMS':>10}{'max|d|':>10}")
    pairs = []
    for i, ya in enumerate(years):
        for yb in years[i + 1 :]:
            a, b = anomalies[ya], anomalies[yb]
            r = pearson(a, b)
            diffs = [x - y for x, y in zip(a, b)]
            rms = math.sqrt(sum(d * d for d in diffs) / len(diffs))
            mx = max(abs(d) for d in diffs)
            abs_r = abs(r) if r is not None else None
            r_s = "n/a" if r is None else f"{r:12.4f}"
            ar_s = "n/a" if abs_r is None else f"{abs_r:10.4f}"
            print(f"{ya}v{yb:<9}{r_s:>12}{ar_s:>10}{rms:10.4f}{mx:10.4f}")
            pairs.append(
                {
                    "pair": f"{ya}v{yb}",
                    "r": r,
                    "abs_r": abs_r,
                    "rms_c": rms,
                    "max_abs_diff_c": mx,
                }
            )

    abs_rs = [p["abs_r"] for p in pairs if p["abs_r"] is not None]
    rms_vals = [p["rms_c"] for p in pairs]
    max_abs_r = max(abs_rs) if abs_rs else float("nan")
    max_rms = max(rms_vals) if rms_vals else float("nan")
    rule = apply_preregistered_rule(max_abs_r, max_rms)

    print()
    print("PRE-REGISTERED RULE (workforce/gate0/PRE_REGISTRATION.md section 2)")
    print("  PASS:        max |r| < 0.70 AND RMS > 0.30 C")
    print("  CONDITIONAL: 0.70 <= max |r| < 0.95")
    print("  FAIL:        max |r| >= 0.95")
    print()
    print(f"primary_metric  max_|r| = {max_abs_r:.4f}")
    print(f"secondary_metric max_RMS = {max_rms:.4f} C")
    print(f"rule_outcome     {rule}   LABEL=RETROSPECTIVE")
    print()
    if rule == "FAIL":
        print("agent_recommendation: Intervention Evidence = NOT BUILT")
        print("human_must_confirm: yes (agents do not close Gate 0)")
    elif rule == "CONDITIONAL":
        print("agent_recommendation: reduced separately-versioned screening, or disable")
        print("human_must_confirm: yes (agents do not close Gate 0)")
    else:
        print("agent_recommendation: Agent G may build modeled Intervention Evidence")
        print("human_must_confirm: yes (agents do not close Gate 0)")

    summary = {
        "label": "RETROSPECTIVE",
        "credits_spent": 0,
        "source_kind": source_kind,
        "source_path": str(source_path),
        "n_tiles": len(keys),
        "years": years,
        "year_stats": year_stats,
        "pairs": pairs,
        "max_abs_r": max_abs_r,
        "max_rms_c": max_rms,
        "rule_outcome": rule,
        "gate0_closed": False,
    }
    out_dir = ROOT / "workforce" / "gate0"
    out_dir.mkdir(parents=True, exist_ok=True)
    out_path = out_dir / "static_field_recompute.json"
    out_path.write_text(json.dumps(summary, indent=2), encoding="utf-8")
    print()
    print(f"wrote {out_path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
