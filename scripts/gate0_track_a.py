"""Track A live multi-AOI TCM test.

Pre-registration must already exist. This script must not change date, hour,
bands, or AOI geometries. Load the API key from workforce/context/05_code/.env
and never print it.

Resume: AOIs with an existing sanitized result file are not re-requested.
"""

from __future__ import annotations

import json
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import importlib.util

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
PROTOCOL_HOUR = "15:00"
PROTOCOL_GRANULARITY = 100
BAND_MATERIAL = 2.0
BAND_NARROW = 0.5

AOI_PATH = ROOT / "workforce" / "gate0" / "track_a" / "aois_preregistered.json"
OUT_DIR = ROOT / "workforce" / "gate0" / "track_a"
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


def _tile_values(assembly: Any) -> list[float]:
    values: list[float] = []
    for tile in assembly.tiles:
        for obs in tile.observations:
            stat = obs.statistic.value if hasattr(obs.statistic, "value") else str(obs.statistic)
            if stat == "mean" and obs.value is not None:
                values.append(float(obs.value))
                break
    return values


def _write_lock() -> None:
    if LOCK_PATH.is_file():
        existing = json.loads(LOCK_PATH.read_text(encoding="utf-8"))
        if existing.get("start_date") != PROTOCOL_DATE or existing.get("start_time") != PROTOCOL_HOUR:
            raise SystemExit("EXECUTION_LOCK date/hour disagrees with frozen protocol")
        return
    LOCK_PATH.write_text(
        json.dumps(
            {
                "frozen": True,
                "first_request_at_utc": datetime.now(timezone.utc).isoformat(),
                "start_date": PROTOCOL_DATE,
                "start_time": PROTOCOL_HOUR,
                "granularity": PROTOCOL_GRANULARITY,
                "analytic_type": "tcm",
                "temporal_mode": "single_hour",
            },
            indent=2,
        ),
        encoding="utf-8",
    )


def main() -> int:
    prereg = json.loads(AOI_PATH.read_text(encoding="utf-8"))
    if prereg.get("tcm_results_observed"):
        print("WARNING: AOI file already marked observed")
    aois = prereg["aois"]
    if len(aois) < 5:
        raise SystemExit("Need five pre-registered AOIs")

    SANITIZED_DIR.mkdir(parents=True, exist_ok=True)
    CACHE_DIR.mkdir(parents=True, exist_ok=True)
    _write_lock()

    api_key = _load_api_key()
    adapter = FortyGuardAdapter(
        api_key=api_key,
        cache_dir=CACHE_DIR,
        fixture_dir=SANITIZED_DIR,
        poll_interval=3.0,
        poll_timeout=600.0,
    )

    per_aoi: list[dict[str, Any]] = []
    if RESULTS_PATH.is_file():
        prior = json.loads(RESULTS_PATH.read_text(encoding="utf-8"))
        per_aoi = list(prior.get("aois") or [])

    by_id = {row["aoi_id"]: row for row in per_aoi}

    for spec in aois:
        aoi_id = spec["aoi_id"]
        out_file = SANITIZED_DIR / f"{aoi_id}.json"
        if aoi_id in by_id and by_id[aoi_id].get("ok") and out_file.is_file():
            print(f"SKIP {aoi_id} (already sanitized)")
            continue

        request = HeatmapFetchRequest(
            polygon_aoi=spec["polygon_aoi"],
            start_date=PROTOCOL_DATE,
            start_time=PROTOCOL_HOUR,
            temporal_mode=HeatmapTemporalMode.SINGLE_HOUR,
            granularity=PROTOCOL_GRANULARITY,
            analytic_type="tcm",
            data_mode=DataMode.LIVE,
        )
        print(f"REQUEST {aoi_id} LIVE {PROTOCOL_DATE} {PROTOCOL_HOUR} gran={PROTOCOL_GRANULARITY}")
        try:
            assembly = adapter.fetch_heatmap(request)
        except Exception as exc:  # noqa: BLE001 — record and continue remaining AOIs
            row = {
                "aoi_id": aoi_id,
                "ok": False,
                "error": type(exc).__name__,
                "error_detail": str(exc)[:500],
            }
            by_id[aoi_id] = row
            _dump_results(list(by_id.values()), complete=False)
            print(f"FAIL {aoi_id}: {type(exc).__name__}")
            continue

        values = _tile_values(assembly)
        missing = sum(1 for tile in assembly.tiles if not tile.observations)
        mean_c = sum(values) / len(values) if values else None
        stats = assembly.stats_data or {}
        temp_stats = stats.get("temperature_stats") or {}
        cache_hit = adapter.cache.get(assembly.fingerprint)
        raw_payload = cache_hit[0] if cache_hit else {"result": {}, "activity_id": None}
        sanitized = sanitize_document(
            raw_payload if isinstance(raw_payload, dict) else {"result": raw_payload},
            request={
                "polygon_aoi": spec["polygon_aoi"],
                "start_date": PROTOCOL_DATE,
                "start_time": PROTOCOL_HOUR,
                "filter_type": 1,
                "granularity": PROTOCOL_GRANULARITY,
                "analytic_type": "tcm",
                "temporal_mode": "single_hour",
            },
            max_tiles=10_000,
            source_name=f"track_a_{aoi_id}",
            label=aoi_id,
        )
        # Keep full tile set for Gate 0 replay; drop bulky blobs already handled.
        result = sanitized["result"]
        stats_out = dict(result.get("stats_data") or {})
        for blob in _DROP_STATS:
            stats_out.pop(blob, None)
        result["stats_data"] = stats_out
        sanitized["activity_id"] = (
            raw_payload.get("activity_id") if isinstance(raw_payload, dict) else None
        )
        sanitized = redact_secrets(sanitized)
        out_file.write_text(json.dumps(sanitized, indent=2, default=str), encoding="utf-8")

        row = {
            "aoi_id": aoi_id,
            "ok": True,
            "label": spec["label"],
            "urban_form": spec["urban_form"],
            "area_km2": spec["area_km2"],
            "request": {
                "start_date": PROTOCOL_DATE,
                "start_time": PROTOCOL_HOUR,
                "temporal_mode": "single_hour",
                "granularity": PROTOCOL_GRANULARITY,
                "analytic_type": "tcm",
                "data_mode": "live",
            },
            "tile_count": len(assembly.tiles),
            "tiles_with_mean": len(values),
            "tiles_missing_observations": missing,
            "aoi_mean_tcm_c": mean_c,
            "tile_min_c": min(values) if values else None,
            "tile_max_c": max(values) if values else None,
            "upstream_temperature_stats": temp_stats,
            "source": str(assembly.source),
            "data_status": str(assembly.data_status),
            "fingerprint": assembly.fingerprint,
            "quality_flags": list(assembly.quality_flags),
            "completeness": assembly.completeness,
            "sanitized_path": str(out_file.relative_to(ROOT)),
        }
        by_id[aoi_id] = row
        _dump_results(list(by_id.values()), complete=False)
        print(f"OK {aoi_id} n={len(values)} mean={mean_c}")

    ordered = [by_id[spec["aoi_id"]] for spec in aois if spec["aoi_id"] in by_id]
    _dump_results(ordered, complete=True)
    prereg["tcm_results_observed"] = True
    AOI_PATH.write_text(json.dumps(prereg, indent=2), encoding="utf-8")
    summary = json.loads(RESULTS_PATH.read_text(encoding="utf-8"))
    print(
        "DONE",
        f"n_ok={summary['n_aois_ok']}",
        f"range={summary['between_aoi_range_c']}",
        f"class={summary['band_classification']}",
    )
    return 0


def _dump_results(rows: list[dict[str, Any]], *, complete: bool) -> None:
    ok_means = [r["aoi_mean_tcm_c"] for r in rows if r.get("ok") and r.get("aoi_mean_tcm_c") is not None]
    range_c = (max(ok_means) - min(ok_means)) if len(ok_means) >= 2 else None
    payload = {
        "label": "TRACK_A_LIVE",
        "gate0_closed": False,
        "complete": complete,
        "credits_note": "Live heatmap calls via FortyGuardAdapter; exact credit delta not metered here.",
        "start_date": PROTOCOL_DATE,
        "start_time": PROTOCOL_HOUR,
        "granularity": PROTOCOL_GRANULARITY,
        "n_aois_ok": sum(1 for r in rows if r.get("ok")),
        "between_aoi_range_c": range_c,
        "band_classification": _classify(range_c) if complete and len(ok_means) >= 5 else None,
        "bands_frozen": {"material_c": BAND_MATERIAL, "narrow_c": BAND_NARROW},
        "aois": rows,
        "classification_rule": (
            ">=2.0 MATERIAL_RANKING_SUPPORTED; "
            ">=0.5 and <2.0 NARROW_SEPARATION_RANKING_WITH_LIMITATIONS; "
            "<0.5 NO_SPATIAL_THERMAL_RANKING_CLAIM"
        ),
        "do_not_reinterpret_bands_after_results": True,
    }
    RESULTS_PATH.write_text(json.dumps(payload, indent=2, default=str), encoding="utf-8")
    md = OUT_DIR / "RESULTS.md"
    md.write_text(_to_markdown(payload), encoding="utf-8")


def _to_markdown(payload: dict[str, Any]) -> str:
    lines = [
        "# Track A results",
        "",
        f"- Date/hour frozen: `{payload['start_date']}` `{payload['start_time']}`",
        f"- Complete: {payload['complete']}",
        f"- n_aois_ok: {payload['n_aois_ok']}",
        f"- between_aoi_range_c: {payload['between_aoi_range_c']}",
        f"- band_classification: {payload['band_classification']}",
        "",
        "| aoi_id | area_km2 | tiles | mean_C | min_C | max_C | source | ok |",
        "|---|---:|---:|---:|---:|---:|---|---|",
    ]
    for row in payload["aois"]:
        lines.append(
            "| {aoi_id} | {area} | {n} | {mean} | {mn} | {mx} | {src} | {ok} |".format(
                aoi_id=row.get("aoi_id"),
                area=row.get("area_km2", ""),
                n=row.get("tile_count", ""),
                mean=row.get("aoi_mean_tcm_c", row.get("error")),
                mn=row.get("tile_min_c", ""),
                mx=row.get("tile_max_c", ""),
                src=row.get("source", row.get("error", "")),
                ok=row.get("ok"),
            )
        )
    lines.extend(
        [
            "",
            "Bands were not reinterpreted after observing results.",
            "Gate 0 remains open.",
            "",
        ]
    )
    return "\n".join(lines) + "\n"


if __name__ == "__main__":
    raise SystemExit(main())
