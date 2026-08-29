"""Replay analysis orchestrator. Gate 0 OPEN: do not emit calibrated P(event)."""

from __future__ import annotations

import json
from collections.abc import Callable
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any
from uuid import uuid4

from app.core.area_config import AreaConfig
from app.core.area_registry import (
    AreaRegistryError,
    resolve_ready_area_package,
)
from app.core.jobs import job_store
from app.core.phoenix_v1_area_config import (
    CANONICAL_REFERENCE_RELATIVE_PATH,
    frozen_area_config_sha256,
    hackathon_root,
    load_frozen_phoenix_v1_area_config,
)
from app.core.versioning import stamp_analysis_versions
from app.domain.enums import (
    AnalysisMode,
    DataMode,
    DataStatus,
    HeatmapTemporalMode,
    JobStatus,
    ReferenceEvidenceQuality,
    ResultStatus,
    SystemLimitationCode,
    ThermalDataSource,
    ThermalDifferentiationState,
    UpstreamTimeSemantics,
)
from app.domain.phoenix_v1 import (
    FROZEN_AREA_CONFIG_SHA256,
    INPUT_QUANTITY,
    METRIC_TOP3_BOTTOM3,
    REFERENCE_HOUR_LOCAL,
    REFERENCE_VERSION,
    REFERENCE_YEARS,
    ZONE_GEOMETRY_VERSION,
)
from app.domain.requests import AnalysisRequest
from app.domain.results import (
    AnalysisResult,
    Confidence,
    EngineResult,
    HazardSpreadProvenance,
    ZoneDecisionResult,
)
from app.integrations.fortyguard import ADAPTER_VERSION, FortyGuardAdapter
from app.integrations.fortyguard.transport_models import HeatmapFetchRequest
from app.services.evidence_builder import (
    build_phoenix_v1_evidence_graph,
    build_replay_evidence_graph,
)
from app.services.phoenix_v1_reference import load_phoenix_v1_reference_panel
from app.services.phoenix_v1_thermal import evaluate_phoenix_v1_timestamp
from app.services.temporal_anomaly import ReferenceObservation
from app.services.zone_aggregator import aggregate_tiles_to_zones

EVENT_PROBABILITY_BLOCKED_PENDING_GATE0 = "EVENT_PROBABILITY_BLOCKED_PENDING_GATE0"
ANALYSIS_TIME_NOT_AOI_LOCAL = "ANALYSIS_TIME_NOT_AOI_LOCAL"
HAZARD_SPREAD_MODULE_UNAVAILABLE = "HAZARD_SPREAD_MODULE_UNAVAILABLE"
ENGINE_NOT_IMPLEMENTED = "ENGINE_NOT_IMPLEMENTED"
INSUFFICIENT_REFERENCE = SystemLimitationCode.INSUFFICIENT_REFERENCE.value
CONTEXTUAL_PREPAREDNESS_PRIORITY = (
    "CONTEXTUAL PREPAREDNESS PRIORITY — THERMAL DIFFERENTIATION UNAVAILABLE"
)
PHOENIX_DEMO_AREA_ID = "phoenix-demo"
# America/Phoenix is UTC-7 year-round. Not a thermal probe number.
PHOENIX_AOI_UTC_OFFSET = timedelta(hours=-7)
BLOCKED_PROBABILITY_MODEL_VERSION = "blocked-pending-gate0"
_MISSING = object()

_API_ROOT = Path(__file__).resolve().parents[2]
_HOURLY_TCM_FIXTURE = (
    _API_ROOT / "tests" / "fixtures" / "fortyguard" / "heatmap_tcm_hourly_1500.json"
)
_UNFROZEN_DEMO_ZONES = (
    _API_ROOT
    / "tests"
    / "fixtures"
    / "orchestrator"
    / "phoenix_demo_unfrozen_zones.geojson"
)
_HOURLY_TCM_LABEL = "heatmap_tcm_hourly_1500.json"

StatusCallback = Callable[[JobStatus], None]

__all__ = [
    "ANALYSIS_TIME_NOT_AOI_LOCAL",
    "EVENT_PROBABILITY_BLOCKED_PENDING_GATE0",
    "execute_job",
    "run_replay_analysis",
]


def _analysis_time_is_aoi_local(analysis_time: datetime) -> bool:
    if analysis_time.tzinfo is None:
        return True
    offset = analysis_time.utcoffset()
    if offset is None:
        return True
    return offset == PHOENIX_AOI_UTC_OFFSET


def _blocked_probability(evidence_refs: list[str]) -> EngineResult[Any]:
    return EngineResult[Any](
        status=ResultStatus.INSUFFICIENT_EVIDENCE,
        value=None,
        confidence=Confidence(score=0.0, band="none"),
        confidence_reasons=[
            "Gate 0 is open; calibrated P(event) is not authorized."
        ],
        evidence_refs=evidence_refs,
        quality_flags=[EVENT_PROBABILITY_BLOCKED_PENDING_GATE0],
        model_version=BLOCKED_PROBABILITY_MODEL_VERSION,
    )


def _unbuilt_engine(evidence_refs: list[str]) -> EngineResult[Any]:
    return EngineResult[Any](
        status=ResultStatus.INSUFFICIENT_EVIDENCE,
        value=None,
        confidence=Confidence(score=0.0, band="none"),
        confidence_reasons=["Engine is not implemented."],
        evidence_refs=evidence_refs,
        quality_flags=[ENGINE_NOT_IMPLEMENTED],
        model_version="unbuilt",
    )


def _load_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def _phoenix_demo_heatmap_request() -> HeatmapFetchRequest:
    """Map phoenix-demo replay onto the committed hourly TCM fixture request."""
    doc = _load_json(_HOURLY_TCM_FIXTURE)
    meta_req = dict(doc["meta"]["request"])
    meta_req["temporal_mode"] = meta_req.get("temporal_mode") or "single_hour"
    meta_req["data_mode"] = DataMode.REPLAY.value
    return HeatmapFetchRequest.model_validate(meta_req)


def _aoi_local_valid_time(fetch_request: HeatmapFetchRequest) -> datetime:
    day = datetime.fromisoformat(fetch_request.start_date)
    start_time = fetch_request.start_time or "00:00"
    parts = start_time.strip().replace("Z", "").split(":")
    hour = int(parts[0])
    minute = int(parts[1]) if len(parts) > 1 else 0
    return datetime(day.year, day.month, day.day, hour, minute)


def _statistic_name(statistic: Any) -> str:
    if hasattr(statistic, "value"):
        return str(statistic.value)
    return str(statistic)


def _mean_temperature(tile: Any) -> float | None:
    for observation in tile.observations:
        if _statistic_name(observation.statistic) == "mean":
            return observation.value
    return None


def assembly_tiles_to_geojson(tiles: list[Any]) -> dict[str, Any]:
    features: list[dict[str, Any]] = []
    for tile in tiles:
        features.append(
            {
                "type": "Feature",
                "properties": {
                    "tile_id": tile.tile_id,
                    "average_temperature": _mean_temperature(tile),
                },
                "geometry": tile.geometry,
            }
        )
    return {"type": "FeatureCollection", "features": features}


def _coerce_data_status(value: Any) -> DataStatus:
    if isinstance(value, DataStatus):
        return value
    raw = getattr(value, "value", value)
    return DataStatus(str(raw))


def _load_hazard_spread_module(override: Any) -> Any:
    if override is not _MISSING:
        return override
    try:
        from app.services import hazard_spread as module
    except ImportError:
        return None
    return module


def _unevaluated_decision8_provenance(
    config: AreaConfig,
    *,
    reason: str,
    reference_quality: str = ReferenceEvidenceQuality.INSUFFICIENT_REFERENCE.value,
) -> HazardSpreadProvenance:
    policy = config.hazard_spread_policy
    return HazardSpreadProvenance(
        policy_version=policy.version,
        reference_version=policy.reference_version or REFERENCE_VERSION,
        zone_geometry_version=policy.zone_geometry_version or ZONE_GEOMETRY_VERSION,
        input_quantity=policy.input_quantity or INPUT_QUANTITY,
        metric=policy.metric or METRIC_TOP3_BOTTOM3,
        top_group_size=policy.top_group_size,
        bottom_group_size=policy.bottom_group_size,
        floor=policy.minimum_useful_spread,
        comparison_operator=policy.comparison_operator,
        observed_spread=None,
        differentiation_state=ThermalDifferentiationState.NOT_EVALUATED.value,
        reference_quality=reference_quality,
        suppression_reason=reason,
        historical_years=list(REFERENCE_YEARS),
        reference_hour=REFERENCE_HOUR_LOCAL,
    )


def _phoenix_v1_versions(config: AreaConfig, *, adapter_version: str):
    catalog = config.intervention_catalog_version or "INACTIVE"
    return stamp_analysis_versions(
        area_config_version=config.version,
        zone_definition_version=config.zone_definition_version,
        zone_geometry_version=config.zone_geometry_version,
        thermal_aggregation_version=config.thermal_aggregation.version,
        normalization_registry_version=config.historical_reference_window.version,
        hazard_spread_policy_version=config.hazard_spread_policy.version,
        probability_model_version=BLOCKED_PROBABILITY_MODEL_VERSION,
        consequence_model_version="unbuilt",
        protection_model_version="unbuilt",
        priority_model_version="unbuilt",
        intervention_catalog_version=catalog,
        context_dataset_version=config.historical_reference_window.version,
        fortyguard_adapter_version=adapter_version,
    )


def _reference_runtime_label(source_path: Path) -> str:
    """Expose the clean runtime relative path for provenance."""
    root = hackathon_root()
    resolved = source_path.resolve()
    canonical = (root / CANONICAL_REFERENCE_RELATIVE_PATH).resolve()
    if resolved == canonical:
        return CANONICAL_REFERENCE_RELATIVE_PATH.as_posix()
    try:
        return resolved.relative_to(root).as_posix()
    except ValueError:
        return source_path.name


def _phoenix_v1_target_date(request: AnalysisRequest) -> str | None:
    if request.area_id != PHOENIX_DEMO_AREA_ID:
        return None
    if not _analysis_time_is_aoi_local(request.analysis_time):
        return None
    if request.analysis_time.hour != 3 or request.analysis_time.minute != 0:
        return None
    return request.analysis_time.date().isoformat()


def _emit(callback: StatusCallback | None, status: JobStatus) -> None:
    if callback is not None:
        callback(status)


def _run_phoenix_v1_historical(
    request: AnalysisRequest,
    *,
    config: AreaConfig,
    analysis_id: str | None,
    quality_flags: list[str],
    status_callback: StatusCallback | None,
    target_date: str,
    reference_source_path: Path | None,
    target_observations: list[ReferenceObservation] | None = None,
    data_status: DataStatus | None = None,
) -> AnalysisResult:
    config_sha = frozen_area_config_sha256()
    _emit(status_callback, JobStatus.FETCHING_THERMAL)
    panel = load_phoenix_v1_reference_panel(
        config,
        source_path=reference_source_path,
    )
    _emit(status_callback, JobStatus.ASSEMBLING_PARTITIONS)
    _emit(status_callback, JobStatus.AGGREGATING_ZONES)
    zone_ids = sorted({row.geoid for row in panel.observations if row.date == target_date})
    if not zone_ids and target_observations:
        zone_ids = sorted({row.geoid for row in target_observations})
    _emit(status_callback, JobStatus.NORMALIZING)
    evaluation = evaluate_phoenix_v1_timestamp(
        target_date,
        panel.observations,
        policy=config.hazard_spread_policy,
        target_observations=target_observations,
    )
    _emit(status_callback, JobStatus.VALIDATING_HAZARD_SPREAD)
    _emit(status_callback, JobStatus.COMPUTING)

    decision8_evaluated = (
        evaluation.reference_quality == ReferenceEvidenceQuality.FULL_REFERENCE.value
        and evaluation.differentiation_state
        != ThermalDifferentiationState.NOT_EVALUATED.value
    )
    evidence_graph = build_phoenix_v1_evidence_graph(
        area_id=request.area_id,
        area_config_version=config.version,
        area_config_sha256=config_sha,
        reference_label=_reference_runtime_label(panel.source_path),
        reference_sha256=panel.source_sha256,
        reference_quality=evaluation.reference_quality,
        zone_ids=zone_ids or [zone.geoid for zone in evaluation.zones],
        extra_metadata={
            "request_data_mode": request.data_mode.value,
            "reference_quality": evaluation.reference_quality,
            "decision8_policy_version": config.hazard_spread_policy.version,
            "decision8_evaluated": decision8_evaluated,
            "reference_version": config.historical_reference_window.version,
            "area_config_version": config.version,
            "target_date": target_date,
            "target_observations_supplied": target_observations is not None,
        },
    )
    aggregation_ref = "zone_aggregation"
    zones_out: list[ZoneDecisionResult] = []
    if evaluation.zones:
        for zone in evaluation.zones:
            evidence_refs = [aggregation_ref]
            zones_out.append(
                ZoneDecisionResult(
                    zone_id=zone.geoid,
                    ranked=bool(
                        evaluation.thermal_ordering_permitted and zone.thermal_state_valid
                    ),
                    probability=_blocked_probability(evidence_refs),
                    consequence=_unbuilt_engine(evidence_refs),
                    protection=_unbuilt_engine(evidence_refs),
                    priority=_unbuilt_engine(evidence_refs),
                    quality_flags=list(quality_flags),
                    evidence_refs=evidence_refs,
                    thermal_observation_valid=zone.thermal_state_valid,
                    q_A=zone.q_A,
                    reference_range_status=zone.reference_range_status,
                    reference_range_exceedance_c=zone.reference_range_exceedance_c,
                    thermal_ordering_permitted=evaluation.thermal_ordering_permitted,
                )
            )
    analysis_mode = request.analysis_mode
    if not isinstance(analysis_mode, AnalysisMode):
        analysis_mode = AnalysisMode(str(analysis_mode))
    limitations = [
        "Calibrated P(event) is blocked while Gate 0 is open.",
        "Missing thermal evidence is not treated as safe.",
    ]
    if evaluation.differentiation_state == ThermalDifferentiationState.INSUFFICIENT.value:
        limitations.insert(1, CONTEXTUAL_PREPAREDNESS_PRIORITY)
    elif evaluation.differentiation_state == ThermalDifferentiationState.NOT_EVALUATED.value:
        limitations.insert(
            1,
            "Spatial thermal ranking is withheld until q_A and Decision 8 can be evaluated.",
        )
    return AnalysisResult(
        analysis_id=analysis_id or f"an_{uuid4().hex[:12]}",
        generated_at=datetime.now(timezone.utc),
        analysis_mode=analysis_mode,
        versions=_phoenix_v1_versions(config, adapter_version=ADAPTER_VERSION),
        data_status=data_status or DataStatus.CACHED,
        system_limitations=list(evaluation.system_limitations),
        zones=zones_out,
        portfolio_recommendation=None,
        evidence_graph=evidence_graph,
        limitations=limitations,
        reference_quality=evaluation.reference_quality,
        thermal_differentiation_state=evaluation.differentiation_state,
        hazard_spread=evaluation.provenance,
        area_config_sha256=config_sha,
        reference_source_sha256=panel.source_sha256,
    )


def run_replay_analysis(
    request: AnalysisRequest,
    *,
    adapter: FortyGuardAdapter | None = None,
    hazard_spread_module: Any = _MISSING,
    zones_geojson: dict[str, Any] | None = None,
    status_callback: StatusCallback | None = None,
    analysis_id: str | None = None,
    reference_source_path: Path | None = None,
    target_observations: list[ReferenceObservation] | None = None,
) -> AnalysisResult:
    """Replay / cached historical slice. Never emits a calibrated event probability."""
    if request.data_mode == DataMode.LIVE and target_observations is None:
        raise ValueError(
            "LIVE FortyGuard fetch is not invoked while Gate 0 is open; use replay."
        )
    resolved = resolve_ready_area_package(request.area_id)

    quality_flags: list[str] = []
    if not _analysis_time_is_aoi_local(request.analysis_time):
        quality_flags.append(ANALYSIS_TIME_NOT_AOI_LOCAL)

    _emit(status_callback, JobStatus.LOADING_CONTEXT)
    if resolved.manifest.area_id == PHOENIX_DEMO_AREA_ID:
        config = load_frozen_phoenix_v1_area_config()
        if resolved.manifest.area_config_sha256 != FROZEN_AREA_CONFIG_SHA256:
            raise AreaRegistryError("Phoenix package AreaConfig SHA-256 mismatch")
    else:
        config = resolved.config
    package_reference_path = reference_source_path or resolved.reference_path
    target_date = _phoenix_v1_target_date(request)
    if target_date is not None:
        return _run_phoenix_v1_historical(
            request,
            config=config,
            analysis_id=analysis_id,
            quality_flags=quality_flags,
            status_callback=status_callback,
            target_date=target_date,
            reference_source_path=package_reference_path,
            target_observations=target_observations,
            data_status=(
                DataStatus.LIVE
                if request.data_mode == DataMode.LIVE
                else DataStatus.CACHED
            ),
        )

    zones = zones_geojson or _load_json(_UNFROZEN_DEMO_ZONES)
    fetch_request = _phoenix_demo_heatmap_request()
    valid_time = _aoi_local_valid_time(fetch_request)

    _emit(status_callback, JobStatus.FETCHING_THERMAL)
    fg_adapter = adapter or FortyGuardAdapter(api_key=None)
    assembly = fg_adapter.fetch_heatmap(fetch_request)

    _emit(status_callback, JobStatus.ASSEMBLING_PARTITIONS)
    tiles_geojson = assembly_tiles_to_geojson(assembly.tiles)

    _emit(status_callback, JobStatus.AGGREGATING_ZONES)
    spec = config.thermal_aggregation
    outcomes = aggregate_tiles_to_zones(
        zones_geojson=zones,
        tiles_geojson=tiles_geojson,
        spec=spec,
        expected_tile_counts={},
        valid_time=valid_time,
        source=ThermalDataSource.REPLAY,
        temporal_mode=HeatmapTemporalMode.SINGLE_HOUR,
        upstream_time_semantics=UpstreamTimeSemantics.AOI_LOCAL_TIME,
        resolution_m=request.granularity_m,
    )

    _emit(status_callback, JobStatus.NORMALIZING)
    spread_module = _load_hazard_spread_module(hazard_spread_module)
    spread_flags: list[str] = []
    spread_limitations: list[str] = [INSUFFICIENT_REFERENCE]
    spread_ranked = False
    if spread_module is None:
        spread_flags.append(HAZARD_SPREAD_MODULE_UNAVAILABLE)
    hazard_spread = _unevaluated_decision8_provenance(
        config,
        reason=(
            "Decision 1B historical reference is not attached to this replay slice; "
            "q_A cannot be produced and Decision 8 was not evaluated. "
            "This is not THERMAL_SPATIAL_DIFFERENTIATION_INSUFFICIENT."
        ),
    )

    _emit(status_callback, JobStatus.VALIDATING_HAZARD_SPREAD)
    _emit(status_callback, JobStatus.COMPUTING)

    zone_ids = [outcome.series.zone_id for outcome in outcomes]
    fingerprint = assembly.fingerprint or ""
    evidence_graph = build_replay_evidence_graph(
        area_id=request.area_id,
        fixture_label=_HOURLY_TCM_LABEL,
        fixture_fingerprint=fingerprint,
        adapter_version=getattr(fg_adapter, "version", ADAPTER_VERSION),
        zone_ids=zone_ids,
        extra_metadata={
            "request_data_mode": request.data_mode.value,
            "reference_quality": ReferenceEvidenceQuality.INSUFFICIENT_REFERENCE.value,
            "decision8_policy_version": config.hazard_spread_policy.version,
            "decision8_evaluated": False,
        },
    )
    aggregation_ref = "zone_aggregation"

    zones_out: list[ZoneDecisionResult] = []
    for outcome in outcomes:
        evidence_refs = [aggregation_ref, *outcome.series.evidence_refs]
        ranked = bool(spread_ranked and outcome.ranked)
        zone_flags = [
            *quality_flags,
            *spread_flags,
            *outcome.series.quality_flags,
        ]
        zones_out.append(
            ZoneDecisionResult(
                zone_id=outcome.series.zone_id,
                ranked=ranked,
                probability=_blocked_probability(evidence_refs),
                consequence=_unbuilt_engine(evidence_refs),
                protection=_unbuilt_engine(evidence_refs),
                priority=_unbuilt_engine(evidence_refs),
                quality_flags=zone_flags,
                evidence_refs=evidence_refs,
                thermal_observation_valid=bool(
                    outcome.series.observations
                    and outcome.series.observations[0].value is not None
                ),
                q_A=None,
                thermal_ordering_permitted=False,
            )
        )

    analysis_mode = request.analysis_mode
    if not isinstance(analysis_mode, AnalysisMode):
        analysis_mode = AnalysisMode(str(analysis_mode))

    return AnalysisResult(
        analysis_id=analysis_id or f"an_{uuid4().hex[:12]}",
        generated_at=datetime.now(timezone.utc),
        analysis_mode=analysis_mode,
        versions=_phoenix_v1_versions(
            config,
            adapter_version=getattr(fg_adapter, "version", ADAPTER_VERSION),
        ),
        data_status=_coerce_data_status(assembly.data_status),
        system_limitations=spread_limitations,
        zones=zones_out,
        portfolio_recommendation=None,
        evidence_graph=evidence_graph,
        limitations=[
            "Calibrated P(event) is blocked while Gate 0 is open.",
            "Spatial thermal ranking is withheld until q_A and Decision 8 can be evaluated.",
            "Missing thermal evidence is not treated as safe.",
        ],
        reference_quality=ReferenceEvidenceQuality.INSUFFICIENT_REFERENCE.value,
        thermal_differentiation_state=ThermalDifferentiationState.NOT_EVALUATED.value,
        hazard_spread=hazard_spread,
        area_config_sha256=frozen_area_config_sha256(),
        reference_source_sha256=None,
    )


def execute_job(job_id: str) -> None:
    """Advance a queued job through the replay slice. No-op if the job is gone."""
    job = job_store.get(job_id)
    if job is None:
        return

    def _status(status: JobStatus) -> None:
        job_store.update_status(job_id, status, note=status.value)

    try:
        request = AnalysisRequest.model_validate(job.request)
        result = run_replay_analysis(
            request,
            status_callback=_status,
            analysis_id=job_id,
        )
        completeness = "complete"
        if result.data_status == DataStatus.PARTIAL:
            completeness = "partial"
        terminal = (
            JobStatus.PARTIAL if completeness == "partial" else JobStatus.COMPLETE
        )
        job_store.set_result(
            job_id,
            result.model_dump(mode="json"),
            terminal,
            message="Replay analysis finished. Calibrated P(event) is blocked.",
        )
    except Exception as exc:
        job_store.update_status(
            job_id,
            JobStatus.FAILED,
            message=str(exc),
            note="failed",
        )
