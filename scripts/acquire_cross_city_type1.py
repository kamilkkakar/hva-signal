"""Scoped CROSS_CITY_OBSERVATION_V1 Type-1 acquisition (operator-only).

Does NOT enable hosted live / public real vendor / public allowance.
Loads the server-side project key from an external env file (never prints it).
One city per invocation. ACQ-LEAD must gate sequential cities manually.
"""

from __future__ import annotations

import argparse
import json
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import httpx

ROOT = Path(__file__).resolve().parents[1]
API_ROOT = ROOT / "apps" / "api"
if str(API_ROOT) not in sys.path:
    sys.path.insert(0, str(API_ROOT))

from app.domain.aggregation import default_thermal_aggregation_spec  # noqa: E402
from app.domain.enums import (  # noqa: E402
    HeatmapTemporalMode,
    ThermalDataSource,
    UpstreamTimeSemantics,
)
from app.domain.multicity.city_catalog import resolve_city_aoi  # noqa: E402
from app.domain.multicity.type1_live import (  # noqa: E402
    dry_run_type1_preflight,
    seed_type1_live_cache,
)
from app.domain.multicity.validation_package import (  # noqa: E402
    build_cross_city_validation_package,
)
from app.integrations.fortyguard.adapter import FortyGuardAdapter  # noqa: E402
from app.integrations.fortyguard.cache import FortyGuardCache, redact_secrets  # noqa: E402
from app.integrations.fortyguard.fingerprints import heatmap_fingerprint  # noqa: E402
from app.integrations.fortyguard.partitioning import plan_partitions  # noqa: E402
from app.integrations.fortyguard.transport_models import (  # noqa: E402
    DataMode,
    HeatmapFetchRequest,
    HeatmapTemporalMode as FgTemporalMode,
    ThermalDataSource,
)
from app.services.orchestrator import assembly_tiles_to_geojson  # noqa: E402
from app.services.zone_aggregator import aggregate_tiles_to_zones  # noqa: E402

# Default remains the published CROSS_CITY_OBSERVATION_V1 clock.
DEFAULT_TARGET_LOCAL = datetime(2024, 7, 8, 15, 0, 0)
TARGET_LOCAL = DEFAULT_TARGET_LOCAL  # backward-compat alias for importers/tests
DEFAULT_PROVIDER_UTC = "2024-07-08T22:00:00Z"
PROVIDER_UTC = DEFAULT_PROVIDER_UTC  # backward-compat alias
# Gate-8 matrix clocks + published 15:00 observation (no other spend times).
APPROVED_TARGET_LOCALS = frozenset(
    {
        datetime(2024, 7, 8, 15, 0, 0),
        datetime(2024, 7, 8, 3, 0, 0),
        datetime(2024, 7, 8, 21, 0, 0),
        datetime(2024, 7, 9, 3, 0, 0),
    }
)
AGG_VERSION = "HVA_NATIONAL_THERMAL_AGGREGATION_V1_CENTROID_WITHIN_MEAN"
ENV_CANDIDATES = (
    ROOT / "workforce" / "context" / "05_code" / ".env",
    Path(r"F:\cursor\hackathon\workforce\context\05_code\.env"),
)
EXPECTED_HASH_PREFIX = {
    "los_angeles": "7049e495115c3f6a",
    "las_vegas": "4023d404b44da71b",
    "phoenix": "d3185750f2ef62d3",
    "tucson": "3455b3160a482b8d",
}
CITY_DIR = {
    "Los Angeles": "los_angeles",
    "Las Vegas": "las_vegas",
    "Phoenix": "phoenix",
    "Tucson": "tucson",
}


def parse_approved_local_datetime(value: str | datetime) -> datetime:
    """Parse an approved AOI-local naive hour from the temporal matrix (+ 15:00)."""
    if isinstance(value, datetime):
        parsed = value.replace(tzinfo=None) if value.tzinfo is not None else value
    else:
        text = str(value).strip().replace("Z", "")
        if "T" in text:
            parsed = datetime.fromisoformat(text)
        else:
            parsed = datetime.strptime(text, "%Y-%m-%d %H:%M:%S")
        if parsed.tzinfo is not None:
            parsed = parsed.replace(tzinfo=None)
    if parsed.minute != 0 or parsed.second != 0 or parsed.microsecond != 0:
        raise SystemExit("STOP: local datetime must land on an exact hour")
    if parsed not in APPROVED_TARGET_LOCALS:
        approved = ", ".join(
            t.isoformat(timespec="seconds") for t in sorted(APPROVED_TARGET_LOCALS)
        )
        raise SystemExit(f"STOP: local datetime not in approved matrix set: {approved}")
    return parsed


def provider_utc_iso(timezone_name: str, target_local: datetime) -> str:
    """Convert approved AOI-local wall time to provider UTC contract string."""
    from zoneinfo import ZoneInfo

    aware = target_local.replace(tzinfo=ZoneInfo(timezone_name))
    return aware.astimezone(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def acquisition_out_root(city_id: str, target_local: datetime) -> Path:
    """Keep published 15:00 layout; stamp matched-instant clocks under matched/."""
    base = ROOT / "data" / "acquisitions" / "cross-city" / city_id
    if target_local == DEFAULT_TARGET_LOCAL:
        return base
    stamp = target_local.strftime("%Y%m%dT%H%M%S")
    return base / "matched" / stamp


UPPER_BOUNDS = {
    "los_angeles": 2961,
    "las_vegas": 6775,
    "phoenix": 9534,
    "tucson": 19002,
}
PHOENIX_REF = {"debit": 4220, "tiles": 3749, "km2": 37.49}  # historical demo envelope
# Human-authorized resume model (post-LA calibration).
DEBIT_MODEL = "TYPE1_SINGLE_PARTITION_EMPIRICAL_DEBIT_V1"
DEBIT_EXPECTED = 4220
DEBIT_NORMAL_MIN = 3800
DEBIT_NORMAL_MAX = 4700
DEBIT_REVIEW_MAX = 5000  # 4701–5000 = review but may continue if explained
DEBIT_HARD_STOP = 5000  # >5000 hard stop


def vendor_cache_fingerprint_for_request(request: HeatmapFetchRequest) -> str:
    """Adapter partition fingerprint used by FortyGuardCache / DataMode.LIVE."""
    plans = plan_partitions(request.polygon_aoi)
    if not plans:
        raise SystemExit("STOP: AOI produced zero partitions")
    return heatmap_fingerprint(request, aoi=plans[0].geometry)


def peek_vendor_cache(
    cache_dir: Path | str, request: HeatmapFetchRequest
) -> tuple[str, dict[str, Any]] | None:
    """Return (fingerprint, bundled_payload) on hit; None on miss. No HTTP."""
    fingerprint = vendor_cache_fingerprint_for_request(request)
    hit = FortyGuardCache(cache_dir).get(fingerprint)
    if hit is None:
        return None
    body, _tier = hit
    if not isinstance(body, dict):
        return fingerprint, {"result": body}
    return fingerprint, body


def _load_key_alias() -> tuple[str, str, str]:
    """Return (alias, api_key, base_url). Prefer VALIDATION_B if configured."""
    env_path = next((p for p in ENV_CANDIDATES if p.is_file()), None)
    if env_path is None:
        raise SystemExit("STOP: no server-side key env file found")
    values: dict[str, str] = {}
    for line in env_path.read_text(encoding="utf-8").splitlines():
        stripped = line.strip()
        if not stripped or stripped.startswith("#") or "=" not in stripped:
            continue
        name, raw = stripped.split("=", 1)
        values[name.strip()] = raw.strip().strip('"').strip("'")
    base = values.get("FORTYGUARD_BASE_URL") or "https://api.fortyguard.com"
    vb = values.get("FORTYGUARD_API_KEY_VALIDATION_B") or values.get(
        "FORTYGUARD_VALIDATION_B_API_KEY"
    )
    if vb:
        return "VALIDATION_B", vb, base
    primary = values.get("FORTYGUARD_API_KEY")
    if primary:
        return "PRIMARY", primary, base
    raise SystemExit("STOP: required server-side key alias not configured")


def _usage_remaining(api_key: str, base_url: str) -> dict[str, Any]:
    """POST usage fetch (historically 0 debit). Never log the key."""
    url = base_url.rstrip("/") + "/v1/system/fetch-api-key-usage"
    with httpx.Client(timeout=60.0) as client:
        resp = client.post(url, json={"api_key": api_key})
        resp.raise_for_status()
        body = resp.json() if isinstance(resp.json(), dict) else {}
    # Vendor returns credit_summary at top level (not under data).
    summary = body.get("credit_summary")
    if not isinstance(summary, dict):
        nested = body.get("data")
        if isinstance(nested, dict):
            summary = nested.get("credit_summary") or nested
    if not isinstance(summary, dict):
        summary = {}
    remaining = summary.get("cycle_remaining_credits")
    if remaining is None:
        remaining = summary.get("total_remaining_credits")
    heatmap = None
    breakdown = body.get("activity_breakdown")
    if isinstance(breakdown, list):
        for row in breakdown:
            if isinstance(row, dict) and str(row.get("name", "")).lower().startswith(
                "heatmap"
            ):
                heatmap = {
                    "credits": row.get("credits"),
                    "count": row.get("count"),
                    "unit_implied": (
                        round(float(row["credits"]) / float(row["count"]), 4)
                        if row.get("credits") is not None
                        and row.get("count") not in (None, 0)
                        else None
                    ),
                }
                break
    return {
        "http_status": resp.status_code,
        "remaining": remaining,
        "cycle_credits_used": summary.get("cycle_credits_used"),
        "heatmap": heatmap,
        "summary_keys": sorted(summary.keys()),
    }


def _city_package(city_id: str) -> dict[str, Any]:
    pkg = build_cross_city_validation_package()
    for row in pkg["cities"]:
        if row["city_id"] == city_id:
            return row
    raise SystemExit(f"city {city_id} missing from Validation Package V2")


def _preflight_gate(
    city_name: str,
    key_alias: str,
    *,
    target_local: datetime | None = None,
) -> dict[str, Any]:
    city_id = CITY_DIR[city_name]
    cfg = resolve_city_aoi(city_name)
    local = parse_approved_local_datetime(target_local or DEFAULT_TARGET_LOCAL)
    freeze = json.loads(
        (ROOT / "data" / "areas" / "cross-city" / city_id / "freeze.json").read_text(
            encoding="utf-8"
        )
    )
    v2 = _city_package(city_id)
    # Validation package always stamps VALIDATION_B; fingerprint ignores key alias.
    pre = dry_run_type1_preflight(
        {"city": city_name, "target_local": local, "key_alias": "VALIDATION_B"}
    )
    expected_local = local.isoformat(timespec="seconds")
    expected_provider_local = local.strftime("%Y-%m-%dT%H:%M")
    expected_utc = provider_utc_iso(cfg.timezone, local)
    hash_ok = str(freeze["combined_geometry_hash"]).startswith(EXPECTED_HASH_PREFIX[city_id])
    checks = {
        "city": cfg.city == city_name,
        "geometry_hash": hash_ok,
        "areas_25": freeze["analysis_area_count"] == 25,
        "polygon_aoi": cfg.polygon_aoi.get("type") in {"Polygon", "MultiPolygon"},
        "local_time": pre["local_time"] == expected_local,
        "provider_local": pre["provider_resolved_time"]["provider_payload_local_valid_time"]
        == expected_provider_local,
        "utc_contract": expected_utc.endswith("Z"),
        "timezone": pre["provider_resolved_time"]["timezone"] == cfg.timezone,
        "resolution_100m": pre["resolution"] == "100m",
        "metric_tcm": "TCM" in str(pre["metric"]).upper(),
        "partitions_1": pre["partition_count"] == 1,
        "comparison_geography": pre.get("comparison_geography_version")
        == "CROSS_CITY_COMPARISON_GEOGRAPHY_V1",
        "hosted_live_off": pre["hosted_live_enabled"] is False,
        "public_real_vendor_off": pre["real_vendor_enabled"] is False,
    }
    # Published 15:00 wave still pins Validation Package V2 fingerprints/UTC.
    if local == DEFAULT_TARGET_LOCAL:
        checks["utc_contract"] = v2["utc_timestamp"].startswith(DEFAULT_PROVIDER_UTC.replace("Z", ""))
        checks["request_fp"] = pre["request_fingerprint"] == v2["request_fingerprint"]
        checks["cache_fp"] = pre["cache_fingerprint"] == v2["cache_fingerprint"]
    else:
        # Matched-instant clocks: fingerprints must be stable for this local hour.
        checks["request_fp"] = len(str(pre["request_fingerprint"])) == 64
        checks["cache_fp"] = len(str(pre["cache_fingerprint"])) == 64
        checks["utc_matches_tz"] = expected_utc == provider_utc_iso(cfg.timezone, local)
    failed = [name for name, ok in checks.items() if not ok]
    if failed:
        raise SystemExit(f"STOP: pre-call gate failed: {failed}")
    return {
        "city_name": city_name,
        "city_id": city_id,
        "cfg": cfg,
        "freeze": freeze,
        "v2": v2,
        "preflight": pre,
        "checks": checks,
        "upper_bound": UPPER_BOUNDS[city_id],
        "key_alias_requested": key_alias,
        "target_local": local,
        "provider_utc": expected_utc,
    }


def _aggregate(
    city_id: str,
    tiles_geojson: dict[str, Any],
    *,
    target_local: datetime | None = None,
) -> dict[str, Any]:
    local = parse_approved_local_datetime(target_local or DEFAULT_TARGET_LOCAL)
    geom = json.loads(
        (ROOT / "data" / "areas" / "cross-city" / city_id / "geometry.geojson").read_text(
            encoding="utf-8"
        )
    )
    # Normalize GEOID property
    for feat in geom.get("features", []):
        props = feat.setdefault("properties", {})
        if "GEOID" not in props and "geoid" in props:
            props["GEOID"] = props["geoid"]
        if "zone_id" not in props and "GEOID" in props:
            props["zone_id"] = props["GEOID"]
    spec = default_thermal_aggregation_spec(AGG_VERSION, minimum_coverage_ratio=None)
    # Force national aggregation version stamp
    spec = spec.model_copy(update={"version": AGG_VERSION})
    expected = {
        str(f["properties"].get("GEOID") or f["properties"].get("zone_id")): 1.0
        for f in geom.get("features", [])
    }
    outcomes = aggregate_tiles_to_zones(
        geom,
        tiles_geojson,
        spec=spec,
        expected_tile_counts=expected,
        valid_time=local,
        source=ThermalDataSource.FORTYGUARD_LIVE,
        temporal_mode=HeatmapTemporalMode.SINGLE_HOUR,
        upstream_time_semantics=UpstreamTimeSemantics.AOI_LOCAL_TIME,
        resolution_m=100,
        zone_id_property="GEOID",
        temperature_property="average_temperature",
    )
    rows = []
    usable = 0
    missing = []
    values = []
    for out in outcomes:
        mean = out.series.observations[0].value if out.series.observations else None
        ok = mean is not None and out.result_status == "ok"
        if ok:
            usable += 1
            values.append(float(mean))
        else:
            missing.append(
                {
                    "area_id": out.series.zone_id,
                    "reason": out.result_status,
                    "tile_count": out.series.tile_count,
                    "quality_flags": list(out.series.quality_flags),
                }
            )
        rows.append(
            {
                "city_id": city_id,
                "area_id": out.series.zone_id,
                "tract_geoid": out.series.zone_id,
                "contributing_cells": out.series.tile_count,
                "mean_tcm_c": mean,
                "usable": ok,
                "coverage_status": out.result_status,
                "aggregation_policy": AGG_VERSION,
            }
        )
    values_sorted = sorted(values)
    mid = values_sorted[len(values_sorted) // 2] if values_sorted else None
    return {
        "aggregation_policy": AGG_VERSION,
        "usable_count": usable,
        "missing_count": len(missing),
        "missing": missing,
        "rows": rows,
        "qa": {
            "min_c": min(values) if values else None,
            "max_c": max(values) if values else None,
            "mean_of_means_c": (sum(values) / len(values)) if values else None,
            "median_c": mid,
            "spread_c": (max(values) - min(values)) if values else None,
            "usable": usable,
            "missing": len(missing),
        },
    }


def acquire_city(
    city_name: str,
    *,
    dry_run: bool = False,
    target_local: datetime | str | None = None,
) -> dict[str, Any]:
    key_alias, api_key, base_url = _load_key_alias()
    local = parse_approved_local_datetime(target_local or DEFAULT_TARGET_LOCAL)
    gate = _preflight_gate(city_name, key_alias, target_local=local)
    city_id = gate["city_id"]
    provider_utc = gate["provider_utc"]
    out_root = acquisition_out_root(city_id, local)
    raw_dir = out_root / "raw"
    norm_dir = out_root / "normalized"
    cache_dir = out_root / "vendor_cache"
    raw_dir.mkdir(parents=True, exist_ok=True)
    norm_dir.mkdir(parents=True, exist_ok=True)
    cache_dir.mkdir(parents=True, exist_ok=True)

    report: dict[str, Any] = {
        "city": city_name,
        "city_id": city_id,
        "key_alias": key_alias,
        "observation_contract": (
            "CROSS_CITY_OBSERVATION_V1"
            if local == DEFAULT_TARGET_LOCAL
            else "CROSS_CITY_MATCHED_INSTANTS_ACQUISITION"
        ),
        "local_timestamp": local.isoformat(timespec="seconds"),
        "provider_utc": provider_utc,
        "timezone": gate["cfg"].timezone,
        "dst_active": gate["v2"].get("dst_active") if local == DEFAULT_TARGET_LOCAL else None,
        "type": "Type-1",
        "metric": "TCM",
        "resolution_m": 100,
        "geometry_version": gate["freeze"]["geometry_version"],
        "geometry_hash": gate["freeze"]["combined_geometry_hash"],
        "area_config_hash": gate["freeze"]["area_config_hash"],
        "request_fingerprint": gate["preflight"]["request_fingerprint"],
        "cache_fingerprint": gate["preflight"]["cache_fingerprint"],
        "partitions": gate["preflight"]["partition_count"],
        "expected_tiles": gate["preflight"]["expected_tiles_estimate"],
        "upper_bound": gate["upper_bound"],
        "preflight_checks": gate["checks"],
        "output_path": str(out_root.relative_to(ROOT).as_posix()),
        "hosted_live_enabled": False,
        "public_real_vendor_enabled": False,
        "public_allowance": 0,
        "vendor_path": "scoped_operator_adapter_LIVE",
    }

    if dry_run:
        report["status"] = "dry_run_gate_pass"
        (out_root / "preflight.json").write_text(
            json.dumps(redact_secrets(report), indent=2), encoding="utf-8"
        )
        print(
            json.dumps(
                {
                    "status": "dry_run_gate_pass",
                    "city": city_name,
                    "key_alias": key_alias,
                    "local_timestamp": report["local_timestamp"],
                    "provider_utc": provider_utc,
                    "output_path": report["output_path"],
                }
            )
        )
        return report

    # Paid path only: ambiguous / completed prior must never silently re-submit.
    # Inspect fingerprint cache, raw artifact, activity_id, normalized result.
    prior = out_root / "provenance.json"
    if prior.is_file():
        existing = json.loads(prior.read_text(encoding="utf-8"))
        prior_status = existing.get("status")
        prior_activity = existing.get("activity_id")
        prior_attempted = bool(existing.get("vendor_attempted"))
        if prior_status == "succeeded" and prior_activity:
            raise SystemExit(
                f"STOP: completed equivalent activity already retained "
                f"({prior_activity}); no second paid request"
            )
        # Timeout/disconnect/failed after vendor window: reconcile only.
        # Do not assume "failed" means the vendor never accepted a submit.
        if prior_attempted or prior_status in {
            "failed",
            "unknown",
            "unknown_vendor_state",
            "recovery_required",
        }:
            raw_activity = None
            raw_audit = out_root / "raw" / "vendor_payload_redacted.json"
            if raw_audit.is_file():
                try:
                    raw_doc = json.loads(raw_audit.read_text(encoding="utf-8"))
                    if isinstance(raw_doc, dict):
                        raw_activity = raw_doc.get("activity_id")
                except json.JSONDecodeError:
                    raw_activity = None
            raise SystemExit(
                "STOP: ambiguous prior execution — do not blind retry. "
                f"Inspect vendor_cache fingerprint under {cache_dir}, "
                f"raw artifact activity_id={raw_activity!r}, "
                f"provenance activity_id={prior_activity!r} status={prior_status!r}, "
                f"normalized under {norm_dir}. Reconcile via activity_id/cache only."
            )

    request = HeatmapFetchRequest(
        polygon_aoi=gate["cfg"].polygon_aoi,
        start_date=local.strftime("%Y-%m-%d"),
        start_time=local.strftime("%H:%M"),
        temporal_mode=FgTemporalMode.SINGLE_HOUR,
        granularity=100,
        analytic_type="tcm",
        data_mode=DataMode.LIVE,
    )
    # Hard cache-first: identical fingerprint never reaches usage or heatmap submit.
    cached = peek_vendor_cache(cache_dir, request)
    if cached is not None:
        adapter_fp, raw_payload = cached
        activity_id = raw_payload.get("activity_id")
        report.update(
            {
                "status": "cache_hit",
                "vendor_attempted": False,
                "debit": 0,
                "debit_source": "cache_reuse_no_new_debit",
                "activity_id": activity_id,
                "adapter_fingerprint": adapter_fp,
                "acquisition_timestamp": datetime.now(timezone.utc).isoformat(),
                "provider_status": "cache_hit",
                "http_status": None,
            }
        )
        (out_root / "provenance.json").write_text(
            json.dumps(redact_secrets(report), indent=2, default=str), encoding="utf-8"
        )
        print(
            json.dumps(
                {
                    "status": "cache_hit",
                    "city": city_name,
                    "vendor_attempted": False,
                    "debit": 0,
                    "activity_id": activity_id,
                    "adapter_fingerprint": adapter_fp,
                }
            )
        )
        return report

    usage_before = _usage_remaining(api_key, base_url)
    report["usage_before"] = {
        "http_status": usage_before["http_status"],
        "remaining": usage_before["remaining"],
        "cycle_credits_used": usage_before.get("cycle_credits_used"),
        "heatmap": usage_before.get("heatmap"),
        "summary_keys": usage_before["summary_keys"],
    }
    report["debit_model"] = DEBIT_MODEL

    adapter = FortyGuardAdapter(
        api_key=api_key,
        base_url=base_url,
        cache_dir=cache_dir,
        poll_interval=3.0,
        poll_timeout=900.0,
    )
    acquired_at = datetime.now(timezone.utc).isoformat()
    print(
        f"ACQUIRE {city_name} LIVE Type-1 TCM 100m partitions=1 "
        f"key_alias={key_alias} (no key value printed)"
    )
    try:
        assembly = adapter.fetch_heatmap(request)
        http_status = 200
        provider_status = "succeeded"
    except Exception as exc:  # noqa: BLE001 — capture; do not auto-retry
        report.update(
            {
                "status": "failed",
                "http_status": getattr(exc, "status_code", None),
                "error_type": type(exc).__name__,
                "error_detail": str(exc)[:500],
                "acquisition_timestamp": acquired_at,
                "vendor_attempted": True,
            }
        )
        (out_root / "provenance.json").write_text(
            json.dumps(redact_secrets(report), indent=2), encoding="utf-8"
        )
        print(json.dumps({"status": "failed", "error": type(exc).__name__}))
        return report

    source_value = (
        assembly.source.value
        if hasattr(assembly.source, "value")
        else str(assembly.source)
    )
    # Defense: adapter LIVE is cache-first; treat any cached assembly as zero debit.
    if source_value == ThermalDataSource.FORTYGUARD_CACHED.value:
        cache_hit = adapter.cache.get(assembly.fingerprint)
        raw_cached = cache_hit[0] if cache_hit else {}
        activity_cached = (
            raw_cached.get("activity_id") if isinstance(raw_cached, dict) else None
        )
        report.update(
            {
                "status": "cache_hit",
                "vendor_attempted": False,
                "debit": 0,
                "debit_source": "adapter_cache_reuse_no_new_debit",
                "activity_id": activity_cached,
                "adapter_fingerprint": assembly.fingerprint,
                "acquisition_timestamp": acquired_at,
                "provider_status": "cache_hit",
                "http_status": http_status,
                "source": source_value,
            }
        )
        (out_root / "provenance.json").write_text(
            json.dumps(redact_secrets(report), indent=2, default=str), encoding="utf-8"
        )
        print(
            json.dumps(
                {
                    "status": "cache_hit",
                    "city": city_name,
                    "vendor_attempted": False,
                    "debit": 0,
                    "activity_id": activity_cached,
                }
            )
        )
        return report

    cache_hit = adapter.cache.get(assembly.fingerprint)
    raw_payload = cache_hit[0] if cache_hit else {"result": {}, "activity_id": None}
    if not isinstance(raw_payload, dict):
        raw_payload = {"result": raw_payload}
    activity_id = raw_payload.get("activity_id")
    result_body = raw_payload.get("result") if isinstance(raw_payload.get("result"), dict) else {}
    tile_count = len(assembly.tiles)
    tiles_with_mean = sum(
        1
        for tile in assembly.tiles
        if any(
            (o.statistic.value if hasattr(o.statistic, "value") else str(o.statistic)) == "mean"
            and o.value is not None
            for o in tile.observations
        )
    )

    usage_after = _usage_remaining(api_key, base_url)
    debit = None
    debit_source = None
    if usage_before["remaining"] is not None and usage_after["remaining"] is not None:
        debit = int(usage_before["remaining"]) - int(usage_after["remaining"])
        debit_source = "cycle_remaining_delta"
    elif (
        usage_before.get("heatmap")
        and usage_after.get("heatmap")
        and usage_before["heatmap"].get("credits") is not None
        and usage_after["heatmap"].get("credits") is not None
    ):
        debit = int(usage_after["heatmap"]["credits"]) - int(
            usage_before["heatmap"]["credits"]
        )
        debit_source = "heatmap_generation_credits_delta"

    # Persist redacted raw audit evidence
    audit_doc = redact_secrets(
        {
            "activity_id": activity_id,
            "adapter_fingerprint": assembly.fingerprint,
            "request_fingerprint": gate["preflight"]["request_fingerprint"],
            "cache_fingerprint": gate["preflight"]["cache_fingerprint"],
            "result": result_body,
            "stats_data": getattr(assembly, "stats_data", None),
            "source": str(assembly.source),
            "data_status": str(assembly.data_status),
        }
    )
    (raw_dir / "vendor_payload_redacted.json").write_text(
        json.dumps(audit_doc, indent=2, default=str), encoding="utf-8"
    )

    tiles_geojson = assembly_tiles_to_geojson(assembly.tiles)
    (raw_dir / "tiles.geojson").write_text(
        json.dumps(tiles_geojson, default=str), encoding="utf-8"
    )

    aggregation = _aggregate(city_id, tiles_geojson, target_local=local)
    (norm_dir / "zone_means.json").write_text(
        json.dumps(
            {
                "city_id": city_id,
                "observation_contract": report["observation_contract"],
                "local_timestamp": local.isoformat(timespec="seconds"),
                "provider_utc": provider_utc,
                "activity_id": activity_id,
                "aggregation": aggregation,
            },
            indent=2,
        ),
        encoding="utf-8",
    )

    # Seed type1_live cache with sanitized runtime-safe payload (no secrets)
    seed_type1_live_cache(
        {
            "city": city_name,
            "target_local": local,
            "key_alias": "VALIDATION_B",
        },
        payload={
            "activity_id": activity_id,
            "city_id": city_id,
            "tile_count": tile_count,
            "zone_means_path": str(
                (norm_dir / "zone_means.json").relative_to(ROOT).as_posix()
            ),
            "qa": aggregation["qa"],
        },
    )

    # Scope / coverage hard stops (independent of debit).
    scope_failures: list[str] = []
    if gate["preflight"]["partition_count"] != 1:
        scope_failures.append("partitions_ne_1")
    if aggregation["usable_count"] < 20:
        scope_failures.append(f"usable_zones_{aggregation['usable_count']}")
    qa = aggregation["qa"]
    if qa.get("min_c") is not None and (qa["min_c"] < -20 or qa["max_c"] > 70):
        scope_failures.append("implausible_temperature_range")

    debit_band = None
    hard_stop = False
    review_band = False
    if debit is None:
        debit_band = "UNKNOWN"
        hard_stop = True
        scope_failures.append("debit_unmetered")
    elif debit > DEBIT_HARD_STOP:
        debit_band = "HARD_STOP"
        hard_stop = True
    elif debit > DEBIT_NORMAL_MAX:
        debit_band = "REVIEW_MAY_CONTINUE"
        review_band = True
    elif debit >= DEBIT_NORMAL_MIN:
        debit_band = "NORMAL"
    else:
        debit_band = "BELOW_NORMAL_REVIEW"
        review_band = True

    if scope_failures:
        hard_stop = True

    report.update(
        {
            "status": "succeeded",
            "http_status": http_status,
            "provider_status": provider_status,
            "activity_id": activity_id,
            "tile_count": tile_count,
            "tiles_with_mean": tiles_with_mean,
            "debit": debit,
            "debit_source": debit_source,
            "usage_after": {
                "http_status": usage_after["http_status"],
                "remaining": usage_after["remaining"],
                "cycle_credits_used": usage_after.get("cycle_credits_used"),
                "heatmap": usage_after.get("heatmap"),
            },
            "circuit_breaker": {
                "model": DEBIT_MODEL,
                "expected": DEBIT_EXPECTED,
                "normal_range": [DEBIT_NORMAL_MIN, DEBIT_NORMAL_MAX],
                "review_max": DEBIT_REVIEW_MAX,
                "hard_stop_gt": DEBIT_HARD_STOP,
                "debit_band": debit_band,
                "triggered": hard_stop,
                "review_band": review_band,
                "scope_failures": scope_failures,
                "legacy_area_upper_bound": gate["upper_bound"],
            },
            "aggregation_qa": aggregation["qa"],
            "usable_25": aggregation["usable_count"] == 25,
            "usable_count": aggregation["usable_count"],
            "missing_areas": aggregation["missing"],
            "acquisition_timestamp": acquired_at,
            "vendor_attempted": True,
            "adapter_fingerprint": assembly.fingerprint,
            "completeness": assembly.completeness,
        }
    )
    (out_root / "provenance.json").write_text(
        json.dumps(redact_secrets(report), indent=2, default=str), encoding="utf-8"
    )
    safe_print = {
        "status": "succeeded",
        "city": city_name,
        "key_alias": key_alias,
        "activity_id": activity_id,
        "tiles": tile_count,
        "debit": debit,
        "debit_band": debit_band,
        "usable": aggregation["usable_count"],
        "qa": aggregation["qa"],
        "circuit_breaker_triggered": hard_stop,
        "scope_failures": scope_failures,
    }
    print(json.dumps(safe_print, indent=2, default=str))
    if hard_stop:
        raise SystemExit(
            f"HARD_STOP after {city_name}: band={debit_band} debit={debit} "
            f"failures={scope_failures}"
        )
    return report


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "city",
        choices=["los_angeles", "las_vegas", "phoenix", "tucson", "LA", "LV", "PHX", "TUC"],
    )
    parser.add_argument("--dry-run", action="store_true")
    parser.add_argument(
        "--local-datetime",
        default=DEFAULT_TARGET_LOCAL.isoformat(timespec="seconds"),
        help=(
            "Approved AOI-local hour from TEMPORAL_PREFLIGHT_MATRIX "
            "(default: 2024-07-08T15:00:00 published observation)."
        ),
    )
    args = parser.parse_args()
    mapping = {
        "los_angeles": "Los Angeles",
        "LA": "Los Angeles",
        "las_vegas": "Las Vegas",
        "LV": "Las Vegas",
        "phoenix": "Phoenix",
        "PHX": "Phoenix",
        "tucson": "Tucson",
        "TUC": "Tucson",
    }
    acquire_city(
        mapping[args.city],
        dry_run=args.dry_run,
        target_local=args.local_datetime,
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
