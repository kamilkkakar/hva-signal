"""Gate 0 between-AOI variance helper. Replay-first. No live HTTP.

Computes between_aoi_range_c only if replay inputs exist that jointly satisfy
the pre-registered protocol:

  same calendar date, same local AOI time, same granularity,
  >=3 separated Phoenix AOIs, analytic_type=tcm, metric on AOI-mean TCM.

Otherwise prints INCOMPLETE_WITHOUT_LIVE_MULTI_AOI and exits 2.
Does not invent AOI means. Does not manufacture differentiation.
Does not spend FortyGuard credits. Does not close Gate 0.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import sys
from collections import defaultdict
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]

CALL_LOGS = [
    ROOT / "workforce" / "context" / "06_live_evidence" / "call_log.jsonl",
    ROOT / "workforce" / "context" / "05_code" / "outputs" / "call_log.jsonl",
]

REPLAY_CANDIDATES = [
    ROOT / "workforce" / "gate0" / "between_aoi_replay.json",
    ROOT / "workforce" / "context" / "06_live_evidence" / "probes" / "between_aoi.json",
]

MIN_AOIS = 3
PASS_C = 0.5
CONDITIONAL_C = 0.1


def aoi_fingerprint(polygon: dict | None) -> str:
    if not polygon:
        return "no_polygon"
    blob = json.dumps(polygon, sort_keys=True, separators=(",", ":"))
    return hashlib.sha1(blob.encode("utf-8")).hexdigest()[:12]


def aoi_bounds(polygon: dict | None) -> dict | None:
    if not polygon:
        return None
    coords = polygon.get("coordinates", [[]])[0]
    lons = [p[0] for p in coords]
    lats = [p[1] for p in coords]
    if not lons or not lats:
        return None
    return {
        "min_lon": min(lons),
        "max_lon": max(lons),
        "min_lat": min(lats),
        "max_lat": max(lats),
    }


def load_call_logs() -> list[dict]:
    rows: list[dict] = []
    seen: set[str] = set()
    for path in CALL_LOGS:
        if not path.is_file():
            continue
        for line in path.read_text(encoding="utf-8").splitlines():
            line = line.strip()
            if not line:
                continue
            rec = json.loads(line)
            key = json.dumps(rec.get("request"), sort_keys=True, default=str)
            fp = rec.get("fingerprint", "")
            dedupe = f"{fp}:{key}"
            if dedupe in seen:
                continue
            seen.add(dedupe)
            rec["_log"] = str(path)
            rows.append(rec)
    return rows


def inventory_from_logs(rows: list[dict]) -> dict:
    heatmap = [
        r
        for r in rows
        if r.get("endpoint") == "/v1/heatmap" and r.get("request", {}).get("analytic_type") == "tcm"
    ]
    groups: dict[tuple, list] = defaultdict(list)
    unique_aois: dict[str, dict] = {}

    for rec in heatmap:
        req = rec.get("request") or {}
        polygon = req.get("polygon_aoi")
        afp = aoi_fingerprint(polygon)
        unique_aois[afp] = {
            "aoi_fingerprint": afp,
            "bounds": aoi_bounds(polygon),
            "label_example": rec.get("label"),
        }
        local_time = req.get("start_time") or "daily_mean"
        key = (req.get("start_date"), local_time, req.get("granularity"), req.get("filter_type"))
        groups[key].append(
            {
                "label": rec.get("label"),
                "fingerprint": rec.get("fingerprint"),
                "cache_file": rec.get("cache_file"),
                "aoi_fingerprint": afp,
                "granularity": req.get("granularity"),
                "start_date": req.get("start_date"),
                "local_time": local_time,
                "filter_type": req.get("filter_type"),
            }
        )

    qualifying = []
    near_misses = []
    for key, members in sorted(groups.items(), key=lambda kv: str(kv[0])):
        aoi_ids = {m["aoi_fingerprint"] for m in members}
        entry = {
            "start_date": key[0],
            "local_time": key[1],
            "granularity": key[2],
            "filter_type": key[3],
            "n_calls": len(members),
            "n_distinct_aois": len(aoi_ids),
            "aoi_fingerprints": sorted(aoi_ids),
            "members": members,
        }
        if len(aoi_ids) >= MIN_AOIS:
            qualifying.append(entry)
        else:
            near_misses.append(entry)

    return {
        "n_unique_phoenix_aois_in_tcm_heatmaps": len(unique_aois),
        "unique_aois": list(unique_aois.values()),
        "qualifying_same_date_time_granularity_ge3_aoi": qualifying,
        "grouped_tcm_calls": near_misses,
        "protocol_satisfied": bool(qualifying),
    }


def load_replay_bundle(path: Path) -> dict:
    data = json.loads(path.read_text(encoding="utf-8"))
    aois = data.get("aois") or []
    means = [float(a["mean_tcm_c"]) for a in aois]
    return {
        "path": str(path),
        "date": data.get("date"),
        "local_time": data.get("local_time"),
        "granularity": data.get("granularity") or data.get("granularity_m"),
        "analytic_type": data.get("analytic_type", "tcm"),
        "aois": aois,
        "means": means,
    }


def protocol_ok(bundle: dict) -> tuple[bool, str]:
    if bundle.get("analytic_type") != "tcm":
        return False, "analytic_type must be tcm"
    if len(bundle.get("aois") or []) < MIN_AOIS:
        return False, f"need >= {MIN_AOIS} AOI means"
    if bundle.get("date") is None or bundle.get("local_time") is None or bundle.get("granularity") is None:
        return False, "date, local_time, and granularity are required"
    ids = {a.get("id") or a.get("aoi_id") for a in bundle["aois"]}
    if len(ids) < MIN_AOIS:
        return False, "AOI ids are not distinct"
    return True, "ok"


def apply_rule(range_c: float) -> str:
    if range_c >= PASS_C:
        return "PASS"
    if range_c >= CONDITIONAL_C:
        return "CONDITIONAL"
    return "FAIL"


def main() -> int:
    parser = argparse.ArgumentParser(description="Gate 0 between-AOI replay diagnostic.")
    parser.add_argument(
        "--replay",
        type=Path,
        default=None,
        help="Optional JSON with >=3 AOI means at same date/time/granularity.",
    )
    args = parser.parse_args()

    print("LIVE_HTTP: forbidden")
    print("CREDITS_SPENT: 0")
    print("gate0_closed: false")
    print()

    rows = load_call_logs()
    inv = inventory_from_logs(rows)
    print("CACHE INVENTORY (tcm heatmaps)")
    print(f"  unique Phoenix AOI polygons: {inv['n_unique_phoenix_aois_in_tcm_heatmaps']}")
    for aoi in inv["unique_aois"]:
        print(f"  - {aoi['aoi_fingerprint']} bounds={aoi['bounds']} label={aoi['label_example']}")
    print(f"  qualifying groups (>=3 AOIs, same date/time/granularity): {len(inv['qualifying_same_date_time_granularity_ge3_aoi'])}")
    print("  grouped tcm calls (not a substitute for the test):")
    for g in inv["grouped_tcm_calls"]:
        print(
            f"    date={g['start_date']} time={g['local_time']} gran={g['granularity']} "
            f"filter={g['filter_type']} distinct_aois={g['n_distinct_aois']}"
        )
    print()

    out_dir = ROOT / "workforce" / "gate0"
    out_dir.mkdir(parents=True, exist_ok=True)
    (out_dir / "cache_inventory.json").write_text(json.dumps(inv, indent=2), encoding="utf-8")

    replay_path = args.replay
    if replay_path is None:
        for candidate in REPLAY_CANDIDATES:
            if candidate.is_file():
                replay_path = candidate
                break

    if replay_path is not None and replay_path.is_file():
        bundle = load_replay_bundle(replay_path)
        ok, reason = protocol_ok(bundle)
        if ok:
            means = bundle["means"]
            range_c = max(means) - min(means)
            rule = apply_rule(range_c)
            print("between_aoi_range_c computed from replay bundle (not live).")
            print(f"  date={bundle['date']} local_time={bundle['local_time']} granularity={bundle['granularity']}")
            print(f"  n_aois={len(means)} means_c={means}")
            print(f"  between_aoi_range_c={range_c:.4f}")
            print(f"  rule_outcome={rule}")
            print("  human_must_confirm: yes (agents do not close Gate 0 / choose zone scale)")
            result = {
                "status": "COMPUTED",
                "between_aoi_range_c": range_c,
                "rule_outcome": rule,
                "bundle": {k: bundle[k] for k in ("path", "date", "local_time", "granularity", "analytic_type")},
                "gate0_closed": False,
            }
            (out_dir / "between_aoi_result.json").write_text(json.dumps(result, indent=2), encoding="utf-8")
            return 0
        print(f"replay bundle present but protocol not satisfied: {reason}")

    if inv["protocol_satisfied"]:
        print("ERROR: inventory claims a qualifying group but no AOI-mean replay bundle was found.")
        print("Refusing to invent AOI means from mixed-granularity or within-AOI splits.")
        return 2

    print("INCOMPLETE_WITHOUT_LIVE_MULTI_AOI")
    print("Existing caches do not jointly satisfy: same date, same local time,")
    print("same granularity, >=3 separated Phoenix AOIs, analytic_type=tcm.")
    print("Two AOIs exist (downtown gran 100; Encanto gran 60). That is not this test.")
    print("Within-AOI Encanto park vs street is a different protocol and must not be reused.")
    print("No live HTTP was issued. Human must authorize any new credit spend.")
    result = {
        "status": "INCOMPLETE_WITHOUT_LIVE_MULTI_AOI",
        "between_aoi_range_c": None,
        "rule_outcome": None,
        "n_unique_aois": inv["n_unique_phoenix_aois_in_tcm_heatmaps"],
        "credits_spent": 0,
        "gate0_closed": False,
    }
    (out_dir / "between_aoi_result.json").write_text(json.dumps(result, indent=2), encoding="utf-8")
    return 2


if __name__ == "__main__":
    raise SystemExit(main())
