"""Gate 0 nighttime tests A (full-day min) and B (03:00 AOI-local).

Pre-registration must exist. Same five Track A AOIs / date / granularity.
Does not change bands, hour, or AOIs after results. Never prints the API key.
"""

from __future__ import annotations

import importlib.util
import json
import math
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
API_ROOT = ROOT / "apps" / "api"
if str(API_ROOT) not in sys.path:
    sys.path.insert(0, str(API_ROOT))

from app.integrations.fortyguard.adapter import FortyGuardAdapter  # noqa: E402
from app.integrations.fortyguard.cache import redact_secrets  # noqa: E402
from app.integrations.fortyguard.transport_models import (  # noqa: E402
    DataMode,
    HeatmapFetchRequest,
    HeatmapTemporalMode,
)

_spec = importlib.util.spec_from_file_location(
    "sanitize_fortyguard_fixture",
    ROOT / "scripts" / "sanitize_fortyguard_fixture.py",
)
_sanitize_mod = importlib.util.module_from_spec(_spec)
assert _spec.loader is not None
_spec.loader.exec_module(_sanitize_mod)
sanitize_document = _sanitize_mod.sanitize_document

PROTOCOL_DATE = "2024-07-15"
PROTOCOL_HOUR_03 = "03:00"
PROTOCOL_GRANULARITY = 100
BAND_MATERIAL = 2.0
BAND_NARROW = 0.5
DAYTIME_SPREAD_C = 0.20036682740606437  # Track A frozen result; diagnostic denominator only

AOI_PATH = ROOT / "workforce" / "gate0" / "track_a" / "aois_preregistered.json"
DAY_RESULTS = ROOT / "workforce" / "gate0" / "track_a" / "RESULTS.json"
OUT_DIR = ROOT / "workforce" / "gate0" / "nighttime"
SANITIZED_DIR = OUT_DIR / "raw_sanitized"
CACHE_DIR = OUT_DIR / "cache"
LOCK_PATH = OUT_DIR / "EXECUTION_LOCK.json"
RESULTS_PATH = OUT_DIR / "RESULTS.json"
ENV_PATH = ROOT / "workforce" / "context" / "05_code" / ".env"

_DROP_STATS = {
    "overall_temperature_distribution",
    "normal_temperature_distribution",
    "temperature_frequency",
}


def _load_api_key() -> str:
    if not ENV_PATH.is_file():
        raise SystemExit(f"Missing {ENV_PATH}")
    for line in ENV_PATH.read_text(encoding="utf-8").splitlines():
        stripped = line.strip()
        if stripped.startswith("FORTYGUARD_API_KEY=") and not stripped.startswith("#"):
            value = stripped.split("=", 1)[1].strip().strip('"').strip("'")
            if value:
                return value
    raise SystemExit("FORTYGUARD_API_KEY not found in env file")


def _classify(range_c: float | None) -> str | None:
    if range_c is None:
        return None
    if range_c >= BAND_MATERIAL:
        return "MATERIAL_RANKING_SUPPORTED"
    if range_c >= BAND_NARROW:
        return "NARROW_SEPARATION_RANKING_WITH_LIMITATIONS"
    return "NO_SPATIAL_THERMAL_RANKING_CLAIM"


def _sample_sd(values: list[float]) -> float | None:
    n = len(values)
    if n < 2:
        return 0.0 if n == 1 else None
    mean = sum(values) / n
    var = sum((x - mean) ** 2 for x in values) / (n - 1)
    return math.sqrt(var)


def _tile_stat(assembly: Any, statistic: str) -> list[float]:
    values: list[float] = []
    for tile in assembly.tiles:
        hit = None
        for obs in tile.observations:
            stat = obs.statistic.value if hasattr(obs.statistic, "value") else str(obs.statistic)
            if stat == statistic and obs.value is not None:
                hit = float(obs.value)
                break
        if hit is not None:
            values.append(hit)
    return values


def _write_lock() -> None:
    if LOCK_PATH.is_file():
        existing = json.loads(LOCK_PATH.read_text(encoding="utf-8"))
        if existing.get("start_date") != PROTOCOL_DATE or existing.get("start_time_03") != PROTOCOL_HOUR_03:
            raise SystemExit("EXECUTION_LOCK disagrees with frozen nighttime protocol")
        return
    LOCK_PATH.write_text(
        json.dumps(
            {
                "frozen": True,
                "covers": ["daily_night_minimum", "fixed_03h_aoi_local"],
                "first_request_at_utc": datetime.now(timezone.utc).isoformat(),
                "start_date": PROTOCOL_DATE,
                "start_time_03": PROTOCOL_HOUR_03,
                "granularity": PROTOCOL_GRANULARITY,
                "analytic_type": "tcm",
                "bands_c": {"material": BAND_MATERIAL, "narrow": BAND_NARROW},
                "do_not_substitute_hour": True,
            },
            indent=2,
        ),
        encoding="utf-8",
    )


def _sanitize_and_write(
    *,
    aoi_id: str,
    suffix: str,
    spec: dict[str, Any],
    request: HeatmapFetchRequest,
    assembly: Any,
    raw_payload: Any,
    filter_type: int,
    temporal_mode: str,
    start_time: str | None,
) -> Path:
    out_file = SANITIZED_DIR / f"{aoi_id}_{suffix}.json"
    req_body = {
        "polygon_aoi": spec["polygon_aoi"],
        "start_date": PROTOCOL_DATE,
        "start_time": start_time,
        "filter_type": filter_type,
        "granularity": PROTOCOL_GRANULARITY,
        "analytic_type": "tcm",
        "temporal_mode": temporal_mode,
    }
    sanitized = sanitize_document(
        raw_payload if isinstance(raw_payload, dict) else {"result": raw_payload},
        request=req_body,
        max_tiles=10_000,
        source_name=f"night_{aoi_id}_{suffix}",
        label=f"{aoi_id}_{suffix}",
    )
    result = sanitized["result"]
    stats_out = dict(result.get("stats_data") or {})
    for blob in _DROP_STATS:
        stats_out.pop(blob, None)
    result["stats_data"] = stats_out
    sanitized["activity_id"] = (
        raw_payload.get("activity_id") if isinstance(raw_payload, dict) else None
    )
    sanitized["meta"]["fingerprint"] = assembly.fingerprint
    sanitized = redact_secrets(sanitized)
    out_file.write_text(json.dumps(sanitized, indent=2, default=str), encoding="utf-8")
    return out_file


def _fetch(
    adapter: FortyGuardAdapter,
    request: HeatmapFetchRequest,
) -> tuple[Any, Any]:
    assembly = adapter.fetch_heatmap(request)
    cache_hit = adapter.cache.get(assembly.fingerprint)
    raw_payload = cache_hit[0] if cache_hit else {"result": {}, "activity_id": None}
    return assembly, raw_payload


def _row_from_values(
    *,
    spec: dict[str, Any],
    assembly: Any,
    values: list[float],
    label: str,
    sanitized_path: Path,
) -> dict[str, Any]:
    mean_c = sum(values) / len(values) if values else None
    return {
        "aoi_id": spec["aoi_id"],
        "ok": bool(values),
        "label": spec["label"],
        "urban_form": spec["urban_form"],
        "area_km2": spec["area_km2"],
        "statistic_label": label,
        "tile_count": len(assembly.tiles),
        "tiles_with_stat": len(values),
        "aoi_mean_c": mean_c,
        "within_aoi_sample_sd_c": _sample_sd(values),
        "tile_min_c": min(values) if values else None,
        "tile_max_c": max(values) if values else None,
        "source": str(assembly.source),
        "data_status": str(assembly.data_status),
        "fingerprint": assembly.fingerprint,
        "quality_flags": list(assembly.quality_flags),
        "completeness": assembly.completeness,
        "sanitized_path": str(sanitized_path.relative_to(ROOT)),
    }


def main() -> int:
    prereg = json.loads(AOI_PATH.read_text(encoding="utf-8"))
    aois = prereg["aois"]
    if len(aois) != 5:
        raise SystemExit("Night tests require the five Track A AOIs")

    OUT_DIR.mkdir(parents=True, exist_ok=True)
    SANITIZED_DIR.mkdir(parents=True, exist_ok=True)
    CACHE_DIR.mkdir(parents=True, exist_ok=True)
    _write_lock()

    adapter = FortyGuardAdapter(
        api_key=_load_api_key(),
        cache_dir=CACHE_DIR,
        fixture_dir=SANITIZED_DIR,
        poll_interval=3.0,
        poll_timeout=600.0,
    )

    min_rows: dict[str, dict[str, Any]] = {}
    h03_rows: dict[str, dict[str, Any]] = {}
    if RESULTS_PATH.is_file():
        prior = json.loads(RESULTS_PATH.read_text(encoding="utf-8"))
        for row in prior.get("daily_night_minimum", {}).get("aois") or []:
            min_rows[row["aoi_id"]] = row
        for row in prior.get("fixed_03h", {}).get("aois") or []:
            h03_rows[row["aoi_id"]] = row

    for spec in aois:
        aoi_id = spec["aoi_id"]
        min_file = SANITIZED_DIR / f"{aoi_id}_full_day_min.json"
        if not (min_rows.get(aoi_id, {}).get("ok") and min_file.is_file()):
            request = HeatmapFetchRequest(
                polygon_aoi=spec["polygon_aoi"],
                start_date=PROTOCOL_DATE,
                start_time=None,
                temporal_mode=HeatmapTemporalMode.FULL_DAY,
                granularity=PROTOCOL_GRANULARITY,
                analytic_type="tcm",
                data_mode=DataMode.LIVE,
            )
            print(f"REQUEST {aoi_id} FULL_DAY min {PROTOCOL_DATE} gran={PROTOCOL_GRANULARITY}", flush=True)
            try:
                assembly, raw = _fetch(adapter, request)
                values = _tile_stat(assembly, "min")
                path = _sanitize_and_write(
                    aoi_id=aoi_id,
                    suffix="full_day_min",
                    spec=spec,
                    request=request,
                    assembly=assembly,
                    raw_payload=raw,
                    filter_type=3,
                    temporal_mode="full_day",
                    start_time=None,
                )
                min_rows[aoi_id] = _row_from_values(
                    spec=spec,
                    assembly=assembly,
                    values=values,
                    label="DAILY/NIGHT MINIMUM TCM",
                    sanitized_path=path,
                )
                print(f"OK {aoi_id} night_min n={len(values)} mean={min_rows[aoi_id]['aoi_mean_c']}", flush=True)
            except Exception as exc:  # noqa: BLE001
                min_rows[aoi_id] = {
                    "aoi_id": aoi_id,
                    "ok": False,
                    "error": type(exc).__name__,
                    "error_detail": str(exc)[:500],
                }
                print(f"FAIL {aoi_id} night_min: {type(exc).__name__}", flush=True)
            _dump(aois, min_rows, h03_rows, complete=False)
        else:
            print(f"SKIP {aoi_id} night_min", flush=True)

        h03_file = SANITIZED_DIR / f"{aoi_id}_0300.json"
        if not (h03_rows.get(aoi_id, {}).get("ok") and h03_file.is_file()):
            request = HeatmapFetchRequest(
                polygon_aoi=spec["polygon_aoi"],
                start_date=PROTOCOL_DATE,
                start_time=PROTOCOL_HOUR_03,
                temporal_mode=HeatmapTemporalMode.SINGLE_HOUR,
                granularity=PROTOCOL_GRANULARITY,
                analytic_type="tcm",
                data_mode=DataMode.LIVE,
            )
            print(f"REQUEST {aoi_id} 03:00 {PROTOCOL_DATE} gran={PROTOCOL_GRANULARITY}", flush=True)
            try:
                assembly, raw = _fetch(adapter, request)
                values = _tile_stat(assembly, "mean")
                path = _sanitize_and_write(
                    aoi_id=aoi_id,
                    suffix="0300",
                    spec=spec,
                    request=request,
                    assembly=assembly,
                    raw_payload=raw,
                    filter_type=1,
                    temporal_mode="single_hour",
                    start_time=PROTOCOL_HOUR_03,
                )
                h03_rows[aoi_id] = _row_from_values(
                    spec=spec,
                    assembly=assembly,
                    values=values,
                    label="03:00 AOI-local TCM",
                    sanitized_path=path,
                )
                print(f"OK {aoi_id} 03:00 n={len(values)} mean={h03_rows[aoi_id]['aoi_mean_c']}", flush=True)
            except Exception as exc:  # noqa: BLE001
                h03_rows[aoi_id] = {
                    "aoi_id": aoi_id,
                    "ok": False,
                    "error": type(exc).__name__,
                    "error_detail": str(exc)[:500],
                }
                print(f"FAIL {aoi_id} 03:00: {type(exc).__name__}", flush=True)
            _dump(aois, min_rows, h03_rows, complete=False)
        else:
            print(f"SKIP {aoi_id} 03:00", flush=True)

    _dump(aois, min_rows, h03_rows, complete=True)
    summary = json.loads(RESULTS_PATH.read_text(encoding="utf-8"))
    print(
        "DONE",
        f"night_min_range={summary['night_minimum_between_AOI_spread']}",
        f"night_min_class={summary['night_minimum_classification']}",
        f"h03_range={summary['fixed_03h_between_AOI_spread']}",
        f"h03_class={summary['fixed_03h_classification']}",
        f"rule={summary['triggered_rule']}",
        flush=True,
    )
    return 0


def _spread(rows: list[dict[str, Any]]) -> float | None:
    means = [r["aoi_mean_c"] for r in rows if r.get("ok") and r.get("aoi_mean_c") is not None]
    if len(means) < 2:
        return None
    return max(means) - min(means)


def _dump(
    aois: list[dict[str, Any]],
    min_rows: dict[str, dict[str, Any]],
    h03_rows: dict[str, dict[str, Any]],
    *,
    complete: bool,
) -> None:
    min_list = [min_rows[a["aoi_id"]] for a in aois if a["aoi_id"] in min_rows]
    h03_list = [h03_rows[a["aoi_id"]] for a in aois if a["aoi_id"] in h03_rows]
    night_spread = _spread(min_list)
    h03_spread = _spread(h03_list)
    night_class = _classify(night_spread) if complete and len(min_list) == 5 and all(r.get("ok") for r in min_list) else None
    h03_class = _classify(h03_spread) if complete and len(h03_list) == 5 and all(r.get("ok") for r in h03_list) else None

    triggered = None
    if night_class and h03_class:
        both_fail = night_class == "NO_SPATIAL_THERMAL_RANKING_CLAIM" and h03_class == "NO_SPATIAL_THERMAL_RANKING_CLAIM"
        disagree = night_class != h03_class
        if both_fail:
            triggered = "RULE_A_BOTH_NIGHT_TESTS_FAIL"
        elif disagree:
            triggered = "RULE_B_NIGHT_TESTS_DISAGREE"
        else:
            triggered = "NIGHT_TESTS_SAME_BAND"

    night_ratio = (night_spread / DAYTIME_SPREAD_C) if night_spread is not None else None
    h03_ratio = (h03_spread / DAYTIME_SPREAD_C) if h03_spread is not None else None

    payload = {
        "label": "NIGHTTIME_SPATIAL_LIVE",
        "gate0_closed": False,
        "complete": complete,
        "start_date": PROTOCOL_DATE,
        "fixed_03h_aoi_local": PROTOCOL_HOUR_03,
        "granularity": PROTOCOL_GRANULARITY,
        "daytime_between_AOI_spread": DAYTIME_SPREAD_C,
        "daytime_classification": "NO_SPATIAL_THERMAL_RANKING_CLAIM",
        "night_minimum_between_AOI_spread": night_spread,
        "night_minimum_classification": night_class,
        "fixed_03h_between_AOI_spread": h03_spread,
        "fixed_03h_classification": h03_class,
        "night_minimum_to_daytime_ratio": night_ratio,
        "fixed_03h_to_daytime_ratio": h03_ratio,
        "triggered_rule": triggered,
        "bands_frozen": {"material_c": BAND_MATERIAL, "narrow_c": BAND_NARROW},
        "ratios_are_diagnostic_only": True,
        "daily_night_minimum": {
            "label": "DAILY/NIGHT MINIMUM TCM",
            "temporal_mode": "full_day",
            "statistic": "min_temperature",
            "not_a_clock_time": True,
            "aois": min_list,
        },
        "fixed_03h": {
            "label": "03:00 AOI-local TCM",
            "temporal_mode": "single_hour",
            "start_time": PROTOCOL_HOUR_03,
            "statistic": "average_temperature",
            "aois": h03_list,
        },
        "do_not_reinterpret_bands_after_results": True,
        "no_spatial_rescue_after_this_test": True,
    }
    RESULTS_PATH.write_text(json.dumps(payload, indent=2, default=str), encoding="utf-8")
    (OUT_DIR / "RESULTS.md").write_text(_to_markdown(payload), encoding="utf-8")


def _to_markdown(payload: dict[str, Any]) -> str:
    lines = [
        "# Nighttime spatial-differentiation results",
        "",
        f"- Date frozen: `{payload['start_date']}`",
        f"- 03:00 AOI-local frozen: `{payload['fixed_03h_aoi_local']}`",
        f"- Complete: {payload['complete']}",
        f"- Daytime range (Track A): {payload['daytime_between_AOI_spread']}",
        f"- Night-minimum range: {payload['night_minimum_between_AOI_spread']} → {payload['night_minimum_classification']}",
        f"- 03:00 range: {payload['fixed_03h_between_AOI_spread']} → {payload['fixed_03h_classification']}",
        f"- night_min / day ratio: {payload['night_minimum_to_daytime_ratio']}",
        f"- 03:00 / day ratio: {payload['fixed_03h_to_daytime_ratio']}",
        f"- Triggered rule: {payload['triggered_rule']}",
        "",
        "Daily/night-minimum is **not** 03:00 temperature.",
        "Bands were not reinterpreted. Gate 0 remains open. No spatial-rescue follow-on.",
        "",
    ]
    return "\n".join(lines) + "\n"


if __name__ == "__main__":
    raise SystemExit(main())
