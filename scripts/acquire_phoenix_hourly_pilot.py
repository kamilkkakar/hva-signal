#!/usr/bin/env python3
"""Canary-first FortyGuard acquisition for the preregistered Phoenix pilot.

The default ``preflight`` command performs no HTTP and needs no credential.
Paid execution is explicit, sequential, cache-first, and never retries an
ambiguous vendor attempt.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import math
import os
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import httpx

ROOT = Path(__file__).resolve().parents[1]
API_ROOT = ROOT / "apps" / "api"
if str(API_ROOT) not in sys.path:
    sys.path.insert(0, str(API_ROOT))

from app.core.gate0_coverage_registry import (  # noqa: E402
    load_phoenix_expected_tile_coverage_evidence,
)
from app.core.hourly_thermal_pilot_registry import (  # noqa: E402
    PHOENIX_HOURLY_PILOT_MANIFEST_SHA256,
    ResolvedHourlyThermalPilotManifest,
    load_phoenix_hourly_thermal_pilot_manifest,
    request_for_hourly_pilot_slot,
)
from app.domain.aggregation import default_thermal_aggregation_spec  # noqa: E402
from app.domain.enums import (  # noqa: E402
    HeatmapTemporalMode,
    ThermalDataSource,
    UpstreamTimeSemantics,
)
from app.domain.hourly_thermal_pilot import HourlyPilotSlot  # noqa: E402
from app.integrations.fortyguard.adapter import FortyGuardAdapter  # noqa: E402
from app.integrations.fortyguard.cache import (  # noqa: E402
    FortyGuardCache,
    redact_secrets,
)
from app.integrations.fortyguard.partitioning import plan_partitions  # noqa: E402
from app.services.orchestrator import assembly_tiles_to_geojson  # noqa: E402
from app.services.zone_aggregator import (  # noqa: E402
    aggregate_tiles_to_zones,
    assign_tiles_centroid_within,
)

DEFAULT_BASE_URL = "https://api.fortyguard.com"
DEFAULT_STATE_DIR = ROOT / ".runtime" / "phoenix-hourly-pilot-v1"
AREA_CONFIG = ROOT / "data" / "demo" / "phoenix" / "area_config.json"
ZONE_GEOMETRY = ROOT / "data" / "areas" / "phoenix-demo" / "geometry.geojson"


class PilotExecutionError(RuntimeError):
    """A fail-closed acquisition or evidence check rejected execution."""


def _enum_value(value: Any) -> str:
    return str(value.value if hasattr(value, "value") else value)


def _write_json(path: Path, value: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        json.dumps(redact_secrets(value), indent=2, default=str) + "\n",
        encoding="utf-8",
    )


def _read_json(path: Path) -> dict[str, Any]:
    try:
        value = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        raise PilotExecutionError(f"invalid local pilot state: {path}") from exc
    if not isinstance(value, dict):
        raise PilotExecutionError(f"local pilot state must be an object: {path}")
    return value


def _sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _env_values(path: Path | None) -> dict[str, str]:
    values = dict(os.environ)
    if path is None:
        return values
    if not path.is_file():
        raise PilotExecutionError(f"credential env file does not exist: {path}")
    for line in path.read_text(encoding="utf-8").splitlines():
        stripped = line.strip()
        if not stripped or stripped.startswith("#") or "=" not in stripped:
            continue
        name, raw = stripped.split("=", 1)
        values[name.strip()] = raw.strip().strip('"').strip("'")
    return values


def _credential(path: Path | None, *, required: bool) -> tuple[str, str, str] | None:
    values = _env_values(path)
    candidates = (
        ("VALIDATION_B", values.get("FORTYGUARD_API_KEY_VALIDATION_B")),
        ("VALIDATION_B", values.get("FORTYGUARD_VALIDATION_B_API_KEY")),
        ("PRIMARY", values.get("FORTYGUARD_API_KEY")),
    )
    for alias, value in candidates:
        if value and value.strip():
            return (
                alias,
                value.strip(),
                values.get("FORTYGUARD_BASE_URL", DEFAULT_BASE_URL),
            )
    if required:
        raise PilotExecutionError(
            "no FortyGuard credential is configured; set FORTYGUARD_API_KEY "
            "in the process environment or pass --env-file"
        )
    return None


def _usage(api_key: str, base_url: str) -> dict[str, Any]:
    url = base_url.rstrip("/") + "/v1/system/fetch-api-key-usage"
    with httpx.Client(timeout=60.0) as client:
        response = client.post(url, json={"api_key": api_key})
        response.raise_for_status()
        body = response.json()
    if not isinstance(body, dict):
        raise PilotExecutionError("FortyGuard usage response is not an object")
    summary = body.get("credit_summary")
    if not isinstance(summary, dict):
        nested = body.get("data")
        summary = nested.get("credit_summary") if isinstance(nested, dict) else None
    if not isinstance(summary, dict):
        raise PilotExecutionError("FortyGuard usage response lacks credit_summary")
    remaining = summary.get("cycle_remaining_credits")
    if remaining is None:
        remaining = summary.get("total_remaining_credits")
    if isinstance(remaining, bool) or not isinstance(remaining, (int, float)):
        raise PilotExecutionError(
            "FortyGuard usage response lacks numeric remaining credits"
        )
    return {
        "http_status": response.status_code,
        "remaining": int(remaining),
        "cycle_credits_used": summary.get("cycle_credits_used"),
    }


def _slot_dir(state_dir: Path, slot: HourlyPilotSlot) -> Path:
    return state_dir / "slots" / slot.slot_id.replace(":", "-")


def _mean_from_tile(tile: Any) -> float | None:
    for observation in tile.observations:
        if _enum_value(observation.statistic) == "mean":
            return observation.value
    return None


def _reference_zone_means(path: Path, slot_id: str) -> dict[str, float]:
    day, local_time = slot_id.split("T", 1)
    rows: dict[str, float] = {}
    try:
        lines = path.read_text(encoding="utf-8").splitlines()
        documents = [json.loads(line) for line in lines if line.strip()]
    except (OSError, json.JSONDecodeError) as exc:
        raise PilotExecutionError("canary reference panel is malformed") from exc
    for row in documents:
        if (
            isinstance(row, dict)
            and row.get("date") == day
            and row.get("local_time") == local_time
            and row.get("usable") is True
            and row.get("mean_tcm_c") is not None
        ):
            zone_id = str(row.get("geoid") or "").zfill(11)
            if zone_id in rows:
                raise PilotExecutionError("canary reference contains a duplicate zone")
            rows[zone_id] = float(row["mean_tcm_c"])
    return rows


def _field_evidence(
    *,
    resolved: ResolvedHourlyThermalPilotManifest,
    slot: HourlyPilotSlot,
    assembly: Any,
    cache_recheck: Any,
    activity_id: str | None,
    debit: int | None,
    debit_source: str,
) -> tuple[dict[str, Any], dict[str, Any], dict[str, Any]]:
    manifest = resolved.manifest
    coverage = load_phoenix_expected_tile_coverage_evidence(ROOT).evidence
    config = json.loads(AREA_CONFIG.read_text(encoding="utf-8"))
    zones = json.loads(ZONE_GEOMETRY.read_text(encoding="utf-8"))
    expected = {
        row.zone_id: row.expected_tile_count for row in coverage.distribution.zones
    }
    valid_time = datetime.fromisoformat(slot.slot_id)
    tile_geojson = assembly_tiles_to_geojson(assembly.tiles)
    spec = default_thermal_aggregation_spec(
        version=config["thermal_aggregation"]["version"],
        minimum_coverage_ratio=config["thermal_aggregation"]["minimum_coverage_ratio"],
        boundary_behavior=config["thermal_aggregation"]["boundary_behavior"],
        notes=config["thermal_aggregation"].get("notes") or [],
    )
    outcomes = aggregate_tiles_to_zones(
        zones,
        tile_geojson,
        spec=spec,
        expected_tile_counts=expected,
        valid_time=valid_time,
        source=assembly.source,
        temporal_mode=HeatmapTemporalMode.SINGLE_HOUR,
        upstream_time_semantics=UpstreamTimeSemantics.AOI_LOCAL_TIME,
        resolution_m=100,
        zone_id_property="GEOID",
    )
    assignments = assign_tiles_centroid_within(
        zones,
        tile_geojson,
        zone_id_property="GEOID",
    )
    actual_counts = {zone_id: len(assignments.get(zone_id, [])) for zone_id in expected}
    zone_means = {
        outcome.series.zone_id: outcome.series.observations[0].value
        for outcome in outcomes
    }
    mapped_count = sum(actual_counts.values())
    missing_tile_temperature_count = sum(
        _mean_from_tile(tile) is None for tile in assembly.tiles
    )
    tile_ids = [str(tile.tile_id) for tile in assembly.tiles]
    temperatures = [_mean_from_tile(tile) for tile in assembly.tiles]
    cache_tile_ids = [str(tile.tile_id) for tile in cache_recheck.tiles]
    cache_temperatures = [_mean_from_tile(tile) for tile in cache_recheck.tiles]
    source_value = _enum_value(assembly.source)

    checks: dict[str, bool] = {
        "assembly_complete": (
            assembly.completeness == "complete" and not assembly.missing_partition_ids
        ),
        "source_is_live_or_cache": source_value
        in {
            ThermalDataSource.FORTYGUARD_LIVE.value,
            ThermalDataSource.FORTYGUARD_CACHED.value,
        },
        "aoi_local_time_semantics": (
            _enum_value(assembly.upstream_time_semantics) == "aoi_local_time"
        ),
        "request_is_exact_single_hour": (
            assembly.upstream_payload.get("date_time")
            == {
                "start_date": slot.date_local,
                "filter_type": 1,
                "start_time": slot.time_local,
            }
            and assembly.upstream_payload.get("analytic_type") == "tcm"
            and assembly.upstream_payload.get("granularity") == 100
            and assembly.upstream_payload.get("polygon_aoi") == resolved.provider_aoi
        ),
        "request_fingerprint_matches_manifest": (
            assembly.fingerprint == slot.request_fingerprint
        ),
        "expected_field_tile_count": (
            len(assembly.tiles)
            == mapped_count
            == manifest.quality_gates.expected_field_tile_count
        ),
        "exact_zone_tile_counts": actual_counts == expected,
        "unique_tile_ids": len(set(tile_ids)) == len(tile_ids),
        "every_tile_has_temperature": (
            missing_tile_temperature_count == 0
            and all(
                value is not None and math.isfinite(float(value))
                for value in temperatures
            )
            and all(
                getattr(tile, "temperature_unit", "celsius") == "celsius"
                for tile in assembly.tiles
            )
        ),
        "every_zone_has_temperature": (
            len(zone_means) == manifest.quality_gates.expected_zone_count
            and all(value is not None for value in zone_means.values())
        ),
        "cache_recheck_matches": (
            _enum_value(cache_recheck.source)
            == ThermalDataSource.FORTYGUARD_CACHED.value
            and cache_recheck.fingerprint == assembly.fingerprint
            and cache_tile_ids == tile_ids
            and cache_temperatures == temperatures
        ),
        "activity_id_retained": bool(activity_id),
        "debit_is_exactly_metered": debit is not None and debit >= 0,
    }

    canary: dict[str, Any] | None = None
    if slot.phase == "canary":
        gate = manifest.quality_gates.canary
        reference = _reference_zone_means(ROOT / gate.reference_path, slot.slot_id)
        comparable = {
            zone_id: abs(float(zone_means[zone_id]) - expected_value)
            for zone_id, expected_value in reference.items()
            if zone_id in zone_means and zone_means[zone_id] is not None
        }
        mean_abs = sum(comparable.values()) / len(comparable) if comparable else None
        max_abs = max(comparable.values()) if comparable else None
        canary = {
            "reference_zone_count": len(reference),
            "comparable_zone_count": len(comparable),
            "mean_absolute_delta_c": mean_abs,
            "maximum_zone_absolute_delta_c": max_abs,
            "maximum_allowed_mean_absolute_delta_c": (
                gate.maximum_mean_absolute_delta_c
            ),
            "maximum_allowed_zone_absolute_delta_c": (
                gate.maximum_zone_absolute_delta_c
            ),
        }
        checks["canary_reference_complete"] = (
            len(reference) == len(comparable) == gate.required_reference_zone_count
        )
        checks["canary_same_instant_consistent"] = bool(
            mean_abs is not None
            and max_abs is not None
            and mean_abs <= gate.maximum_mean_absolute_delta_c
            and max_abs <= gate.maximum_zone_absolute_delta_c
        )

    normalized = {
        "schema_version": "PHX_HOURLY_PILOT_FIELD_V1",
        "manifest_sha256": resolved.sha256,
        "slot_id": slot.slot_id,
        "area_id": manifest.area_id,
        "timezone": manifest.iana_timezone,
        "geometry_version": coverage.geometry_version,
        "aggregation_spec_version": config["thermal_aggregation"]["version"],
        "source": source_value,
        "mapped_tile_count": mapped_count,
        "zone_count": len(zone_means),
        "zones": [
            {
                "zone_id": zone_id,
                "temperature_c": zone_means[zone_id],
                "tile_count": actual_counts[zone_id],
            }
            for zone_id in sorted(zone_means)
        ],
    }
    evidence = {
        "checks": checks,
        "tile_count_returned": len(assembly.tiles),
        "mapped_tile_count": mapped_count,
        "unassigned_tile_count": len(assignments.get("unassigned", [])),
        "missing_tile_temperature_count": missing_tile_temperature_count,
        "expected_zone_tile_counts": expected,
        "observed_zone_tile_counts": actual_counts,
        "debit": debit,
        "debit_source": debit_source,
        "canary": canary,
    }
    return normalized, tile_geojson, evidence


def _execute_slot(
    *,
    resolved: ResolvedHourlyThermalPilotManifest,
    slot: HourlyPilotSlot,
    state_dir: Path,
    credential: tuple[str, str, str],
) -> dict[str, Any]:
    alias, api_key, base_url = credential
    slot_dir = _slot_dir(state_dir, slot)
    report_path = slot_dir / "report.json"
    attempt_path = slot_dir / "attempt.json"
    cache = FortyGuardCache(state_dir / "vendor_cache")
    request = request_for_hourly_pilot_slot(resolved, slot)

    if report_path.is_file():
        report = _read_json(report_path)
        if (
            report.get("manifest_sha256") == resolved.sha256
            and report.get("slot_id") == slot.slot_id
            and report.get("status") == "PASS"
        ):
            return {**report, "resumed": True}
        raise PilotExecutionError(
            f"existing non-passing report requires review; no automatic retry: {report_path}"
        )

    cached_before = cache.get(slot.request_fingerprint)
    if attempt_path.is_file():
        prior = _read_json(attempt_path)
        if prior.get("vendor_attempted"):
            raise PilotExecutionError(
                f"prior vendor attempt for {slot.slot_id} has no passing report; "
                "reconcile it before retry"
            )

    adapter = FortyGuardAdapter(
        api_key=api_key,
        base_url=base_url,
        cache=cache,
        poll_interval=3.0,
        poll_timeout=900.0,
    )
    usage_before: dict[str, Any] | None = None
    usage_after: dict[str, Any] | None = None
    vendor_attempted = False
    debit: int | None = 0 if cached_before is not None else None
    debit_source = (
        "cache_reuse_no_new_debit" if cached_before is not None else "unmetered"
    )
    _write_json(
        attempt_path,
        {
            "schema_version": "PHX_HOURLY_PILOT_ATTEMPT_V1",
            "manifest_sha256": resolved.sha256,
            "slot_id": slot.slot_id,
            "request_fingerprint": slot.request_fingerprint,
            "credential_alias": alias,
            "vendor_attempted": False,
            "status": "prepared",
            "prepared_at_utc": datetime.now(timezone.utc).isoformat(),
        },
    )
    if cached_before is None:
        usage_before = _usage(api_key, base_url)
        vendor_attempted = True
        _write_json(
            attempt_path,
            {
                "schema_version": "PHX_HOURLY_PILOT_ATTEMPT_V1",
                "manifest_sha256": resolved.sha256,
                "slot_id": slot.slot_id,
                "request_fingerprint": slot.request_fingerprint,
                "credential_alias": alias,
                "vendor_attempted": True,
                "status": "submitted_or_in_progress",
                "usage_before": usage_before,
                "submitted_at_utc": datetime.now(timezone.utc).isoformat(),
            },
        )
    try:
        assembly = adapter.fetch_heatmap(request)
    except Exception as exc:  # noqa: BLE001 - persist fail-closed state, never retry
        _write_json(
            attempt_path,
            {
                "schema_version": "PHX_HOURLY_PILOT_ATTEMPT_V1",
                "manifest_sha256": resolved.sha256,
                "slot_id": slot.slot_id,
                "request_fingerprint": slot.request_fingerprint,
                "credential_alias": alias,
                "vendor_attempted": vendor_attempted,
                "status": "failed_or_unknown_vendor_state",
                "error_type": type(exc).__name__,
                "failed_at_utc": datetime.now(timezone.utc).isoformat(),
            },
        )
        raise PilotExecutionError(
            f"vendor request failed for {slot.slot_id}; no automatic retry"
        ) from exc

    if cached_before is None:
        usage_after = _usage(api_key, base_url)
        debit = usage_before["remaining"] - usage_after["remaining"]
        debit_source = "cycle_remaining_delta"
    cache_payload = cache.get(slot.request_fingerprint)
    raw_payload = cache_payload[0] if cache_payload else {}
    activity_id = (
        raw_payload.get("activity_id") if isinstance(raw_payload, dict) else None
    )
    if cached_before is None:
        _write_json(
            attempt_path,
            {
                "schema_version": "PHX_HOURLY_PILOT_ATTEMPT_V1",
                "manifest_sha256": resolved.sha256,
                "slot_id": slot.slot_id,
                "request_fingerprint": slot.request_fingerprint,
                "credential_alias": alias,
                "vendor_attempted": True,
                "activity_id": activity_id,
                "status": "vendor_completed_metered",
                "usage_before": usage_before,
                "usage_after": usage_after,
                "debit": debit,
                "debit_source": debit_source,
                "metered_at_utc": datetime.now(timezone.utc).isoformat(),
            },
        )
    cache_recheck = adapter.fetch_heatmap(request)
    normalized, tile_geojson, evidence = _field_evidence(
        resolved=resolved,
        slot=slot,
        assembly=assembly,
        cache_recheck=cache_recheck,
        activity_id=activity_id,
        debit=debit,
        debit_source=debit_source,
    )
    _write_json(slot_dir / "raw" / "vendor_payload_redacted.json", raw_payload)
    _write_json(slot_dir / "raw" / "tiles.geojson", tile_geojson)
    _write_json(slot_dir / "normalized" / "zone_means.json", normalized)

    status = "PASS" if all(evidence["checks"].values()) else "FAIL"
    report = {
        "schema_version": "PHX_HOURLY_PILOT_SLOT_REPORT_V1",
        "manifest_sha256": resolved.sha256,
        "slot_id": slot.slot_id,
        "phase": slot.phase,
        "status": status,
        "request_fingerprint": slot.request_fingerprint,
        "credential_alias": alias,
        "vendor_attempted": vendor_attempted,
        "activity_id": activity_id,
        "source": _enum_value(assembly.source),
        "usage_before": usage_before,
        "usage_after": usage_after,
        **evidence,
        "completed_at_utc": datetime.now(timezone.utc).isoformat(),
        "claim_boundary": (
            "acquisition evidence only; does not close Gate 0 or authorize an outcome"
        ),
    }
    _write_json(report_path, report)
    _write_json(
        attempt_path,
        {
            "schema_version": "PHX_HOURLY_PILOT_ATTEMPT_V1",
            "manifest_sha256": resolved.sha256,
            "slot_id": slot.slot_id,
            "request_fingerprint": slot.request_fingerprint,
            "credential_alias": alias,
            "vendor_attempted": vendor_attempted,
            "activity_id": activity_id,
            "status": "completed" if status == "PASS" else "completed_quality_failure",
            "completed_at_utc": report["completed_at_utc"],
        },
    )
    return report


def _preflight(
    resolved: ResolvedHourlyThermalPilotManifest,
    state_dir: Path,
    env_file: Path | None,
) -> dict[str, Any]:
    requests = [
        request_for_hourly_pilot_slot(resolved, slot)
        for slot in resolved.manifest.slots
    ]
    credential = _credential(env_file, required=False)
    report = {
        "schema_version": "PHX_HOURLY_PILOT_PREFLIGHT_V1",
        "status": "PASS",
        "manifest_sha256": resolved.sha256,
        "manifest_version": resolved.manifest.manifest_version,
        "slot_count": len(requests),
        "unique_request_fingerprint_count": len(
            {slot.request_fingerprint for slot in resolved.manifest.slots}
        ),
        "canary_slot_id": resolved.manifest.quality_gates.canary.slot_id,
        "provider_partition_count": len(plan_partitions(resolved.provider_aoi)),
        "credential_available": credential is not None,
        "execution_ready": credential is not None,
        "live_http_performed": False,
        "credits_spent": 0,
    }
    _write_json(state_dir / "preflight.json", report)
    return report


def _require_confirmation(
    value: str, resolved: ResolvedHourlyThermalPilotManifest
) -> None:
    if value != resolved.sha256:
        raise PilotExecutionError(
            "--confirm-manifest-sha must equal the loaded preregistration SHA-256"
        )


def _run_canary(
    args: argparse.Namespace, resolved: ResolvedHourlyThermalPilotManifest
) -> int:
    _require_confirmation(args.confirm_manifest_sha, resolved)
    credential = _credential(args.env_file, required=True)
    assert credential is not None
    slot = next(slot for slot in resolved.manifest.slots if slot.phase == "canary")
    report = _execute_slot(
        resolved=resolved,
        slot=slot,
        state_dir=args.state_dir,
        credential=credential,
    )
    print(
        json.dumps(
            {
                "phase": "canary",
                "slot_id": slot.slot_id,
                "status": report["status"],
                "vendor_attempted": report.get("vendor_attempted"),
                "debit": report.get("debit"),
                "failed_checks": [
                    name
                    for name, passed in report.get("checks", {}).items()
                    if not passed
                ],
            }
        )
    )
    return 0 if report["status"] == "PASS" else 1


def _run_batch(
    args: argparse.Namespace, resolved: ResolvedHourlyThermalPilotManifest
) -> int:
    _require_confirmation(args.confirm_manifest_sha, resolved)
    canary_slot = next(
        slot for slot in resolved.manifest.slots if slot.phase == "canary"
    )
    canary_path = _slot_dir(args.state_dir, canary_slot) / "report.json"
    canary = _read_json(canary_path)
    if (
        canary.get("status") != "PASS"
        or canary.get("manifest_sha256") != resolved.sha256
        or not all(canary.get("checks", {}).values())
    ):
        raise PilotExecutionError(
            "a passing canary for this exact manifest is required"
        )
    credential = _credential(args.env_file, required=True)
    assert credential is not None

    completed: list[dict[str, Any]] = []
    new_requests = 0
    for slot in (slot for slot in resolved.manifest.slots if slot.phase == "batch"):
        report = _execute_slot(
            resolved=resolved,
            slot=slot,
            state_dir=args.state_dir,
            credential=credential,
        )
        completed.append(report)
        if report.get("vendor_attempted") and not report.get("resumed"):
            new_requests += 1
        if report["status"] != "PASS":
            break
        if args.max_new_requests is not None and new_requests >= args.max_new_requests:
            break

    passing = sum(report.get("status") == "PASS" for report in completed)
    total_passing = 1
    for slot in (slot for slot in resolved.manifest.slots if slot.phase == "batch"):
        path = _slot_dir(args.state_dir, slot) / "report.json"
        if path.is_file():
            report = _read_json(path)
            total_passing += int(
                report.get("status") == "PASS"
                and report.get("manifest_sha256") == resolved.sha256
            )
    status = "PASS" if total_passing == resolved.manifest.request_count else "PARTIAL"
    summary = {
        "schema_version": "PHX_HOURLY_PILOT_BATCH_REPORT_V1",
        "manifest_sha256": resolved.sha256,
        "status": status,
        "manifest_slot_count": resolved.manifest.request_count,
        "passing_slot_count": total_passing,
        "slots_processed_this_run": len(completed),
        "passing_slots_this_run": passing,
        "new_vendor_requests_this_run": new_requests,
        "completed_at_utc": datetime.now(timezone.utc).isoformat(),
        "claim_boundary": (
            "pilot completion does not freeze the candidate or authorize an outcome"
        ),
    }
    _write_json(args.state_dir / "batch_report.json", summary)
    print(json.dumps(summary))
    return 0 if status == "PASS" else 2


def _status(
    resolved: ResolvedHourlyThermalPilotManifest, state_dir: Path
) -> dict[str, Any]:
    rows = []
    for slot in resolved.manifest.slots:
        path = _slot_dir(state_dir, slot) / "report.json"
        if path.is_file():
            report = _read_json(path)
            rows.append(
                {
                    "slot_id": slot.slot_id,
                    "phase": slot.phase,
                    "status": report.get("status"),
                    "manifest_matches": report.get("manifest_sha256")
                    == resolved.sha256,
                }
            )
    return {
        "manifest_sha256": resolved.sha256,
        "manifest_slot_count": resolved.manifest.request_count,
        "reported_slot_count": len(rows),
        "passing_slot_count": sum(
            row["status"] == "PASS" and row["manifest_matches"] for row in rows
        ),
        "slots": rows,
    }


def _parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--root", type=Path, default=ROOT)
    parser.add_argument("--state-dir", type=Path, default=DEFAULT_STATE_DIR)
    parser.add_argument(
        "--env-file",
        type=Path,
        default=None,
        help="Optional local credential file; values are never persisted or printed.",
    )
    sub = parser.add_subparsers(dest="command", required=True)
    sub.add_parser("preflight", help="Verify all 72 requests without HTTP.")
    sub.add_parser("status", help="Summarize local execution state without HTTP.")
    canary = sub.add_parser("canary", help="Execute only the frozen 03:00 canary.")
    canary.add_argument("--confirm-manifest-sha", required=True)
    batch = sub.add_parser("batch", help="Resume the 71-slot batch after canary PASS.")
    batch.add_argument("--confirm-manifest-sha", required=True)
    batch.add_argument(
        "--max-new-requests",
        type=int,
        default=None,
        choices=range(1, 72),
        help="Optional operator throttle; omitted means run all remaining slots.",
    )
    return parser


def main() -> int:
    args = _parser().parse_args()
    if args.root.resolve() != ROOT.resolve():
        raise PilotExecutionError("execution must use the checked-out repository root")
    args.state_dir = args.state_dir.resolve()
    args.env_file = args.env_file.resolve() if args.env_file is not None else None
    resolved = load_phoenix_hourly_thermal_pilot_manifest(root=ROOT)
    if resolved.sha256 != PHOENIX_HOURLY_PILOT_MANIFEST_SHA256:
        raise PilotExecutionError(
            "loaded pilot manifest is not the code-authorized SHA"
        )

    if args.command == "preflight":
        print(json.dumps(_preflight(resolved, args.state_dir, args.env_file)))
        return 0
    if args.command == "status":
        print(json.dumps(_status(resolved, args.state_dir)))
        return 0
    if args.command == "canary":
        return _run_canary(args, resolved)
    if args.command == "batch":
        return _run_batch(args, resolved)
    raise PilotExecutionError(f"unknown command {args.command}")


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except PilotExecutionError as exc:
        print(f"STOP: {exc}", file=sys.stderr)
        raise SystemExit(1) from None
