"""Build and SHA-lock the preregistered Phoenix hourly acquisition pilot."""

from __future__ import annotations

import hashlib
import json
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from pydantic import ValidationError
from shapely.geometry import MultiPolygon, Polygon, shape
from shapely.geometry.polygon import orient
from shapely.ops import unary_union

from app.core.gate0_coverage_registry import (
    PHOENIX_COVERAGE_EVIDENCE_RELATIVE_PATH,
    load_phoenix_expected_tile_coverage_evidence,
)
from app.core.hourly_thermal_event_registry import (
    PHOENIX_HOURLY_EVENT_CONTRACT_RELATIVE_PATH,
    load_phoenix_hourly_thermal_event_contract,
)
from app.core.phoenix_v1_area_config import hackathon_root
from app.domain.hourly_thermal_pilot import (
    HourlyPilotCanaryGate,
    HourlyPilotClaimBoundaries,
    HourlyPilotExecutionBoundary,
    HourlyPilotQualityGates,
    HourlyPilotRequestContract,
    HourlyPilotSlot,
    HourlyPilotSource,
    HourlyThermalPilotManifest,
)
from app.domain.phoenix_v1 import (
    AREA_ID,
    EXPECTED_ZONE_COUNT,
    FROZEN_AREA_CONFIG_SHA256,
    GRANULARITY_M,
    PARTITION_STRATEGY,
)
from app.integrations.fortyguard.fingerprints import heatmap_fingerprint
from app.integrations.fortyguard.partitioning import plan_partitions
from app.integrations.fortyguard.transport_models import (
    DataMode,
    HeatmapFetchRequest,
    HeatmapTemporalMode,
)

PHOENIX_HOURLY_PILOT_MANIFEST_RELATIVE_PATH = (
    Path("data") / "gate0" / "phoenix-v1" / "hourly_thermal_pilot_manifest.json"
)
PHOENIX_HOURLY_PILOT_PROVIDER_AOI_RELATIVE_PATH = (
    Path("data") / "gate0" / "phoenix-v1" / "hourly_pilot_provider_aoi.geojson"
)
PHOENIX_HOURLY_PILOT_MANIFEST_SHA256 = (
    "f3505b68dca4279cd9d50c941290c1daf1140707a74ea7686b129f5a8bdf1617"
)

AREA_CONFIG_RELATIVE_PATH = Path("data") / "demo" / "phoenix" / "area_config.json"
AREA_MANIFEST_RELATIVE_PATH = Path("data") / "areas" / "phoenix-demo" / "manifest.json"
ZONE_GEOMETRY_RELATIVE_PATH = (
    Path("data") / "areas" / "phoenix-demo" / "geometry.geojson"
)
CANARY_REFERENCE_RELATIVE_PATH = (
    Path("data") / "phoenix" / "reference" / "observations.jsonl"
)
PILOT_DATES = ("2022-07-15", "2023-07-15", "2024-07-15")
PILOT_HOURS = tuple(f"{hour:02d}:00" for hour in range(24))
CANARY_SLOT_ID = "2024-07-15T03:00"


class HourlyThermalPilotRegistryError(ValueError):
    """The pilot manifest or one of its frozen inputs is invalid."""


@dataclass(frozen=True)
class ResolvedHourlyThermalPilotManifest:
    manifest: HourlyThermalPilotManifest
    path: Path
    sha256: str
    provider_aoi: dict[str, Any]


def _path(root: Path, relative: Path) -> Path:
    candidate = (root / relative).resolve()
    try:
        candidate.relative_to(root.resolve())
    except ValueError as exc:
        raise HourlyThermalPilotRegistryError(
            f"pilot source escapes repository root: {relative.as_posix()}"
        ) from exc
    if not candidate.is_file():
        raise HourlyThermalPilotRegistryError(
            f"pilot source is missing: {relative.as_posix()}"
        )
    return candidate


def _bytes(root: Path, relative: Path) -> bytes:
    return _path(root, relative).read_bytes()


def _sha256(raw: bytes) -> str:
    return hashlib.sha256(raw).hexdigest()


def _json(root: Path, relative: Path) -> dict[str, Any]:
    try:
        value = json.loads(_bytes(root, relative).decode("utf-8"))
    except (UnicodeDecodeError, json.JSONDecodeError) as exc:
        raise HourlyThermalPilotRegistryError(
            f"pilot source is malformed: {relative.as_posix()}"
        ) from exc
    if not isinstance(value, dict):
        raise HourlyThermalPilotRegistryError(
            f"pilot source must be an object: {relative.as_posix()}"
        )
    return value


def _canonical_ring(raw: Any) -> list[list[float]]:
    coords = [[float(point[0]), float(point[1])] for point in raw]
    if len(coords) < 4 or coords[0] != coords[-1]:
        raise HourlyThermalPilotRegistryError("provider AOI contains an open ring")
    body = coords[:-1]
    start = min(range(len(body)), key=lambda index: tuple(body[index]))
    rotated = body[start:] + body[:start]
    return rotated + [rotated[0]]


def _canonical_polygon(polygon: Polygon) -> list[list[list[float]]]:
    directed = orient(polygon, sign=1.0)
    exterior = _canonical_ring(directed.exterior.coords)
    holes = sorted(
        (_canonical_ring(interior.coords) for interior in directed.interiors),
        key=lambda ring: json.dumps(ring, separators=(",", ":")),
    )
    return [exterior, *holes]


def build_phoenix_hourly_pilot_provider_aoi(root: Path) -> dict[str, Any]:
    """Dissolve the exact frozen tract set into one canonical provider polygon."""

    repo = Path(root).resolve()
    document = _json(repo, ZONE_GEOMETRY_RELATIVE_PATH)
    features = document.get("features")
    if document.get("type") != "FeatureCollection" or not isinstance(features, list):
        raise HourlyThermalPilotRegistryError(
            "Phoenix zones are not a FeatureCollection"
        )
    if len(features) != EXPECTED_ZONE_COUNT:
        raise HourlyThermalPilotRegistryError("Phoenix pilot requires exactly 25 zones")
    geoids: list[str] = []
    polygons = []
    for feature in features:
        if not isinstance(feature, dict):
            raise HourlyThermalPilotRegistryError(
                "Phoenix geometry contains an invalid feature"
            )
        properties = feature.get("properties")
        if not isinstance(properties, dict) or not properties.get("GEOID"):
            raise HourlyThermalPilotRegistryError(
                "Phoenix geometry feature is missing GEOID"
            )
        geoids.append(str(properties["GEOID"]).zfill(11))
        polygons.append(shape(feature.get("geometry")))
    if len(set(geoids)) != EXPECTED_ZONE_COUNT:
        raise HourlyThermalPilotRegistryError(
            "Phoenix pilot zone identities are not unique"
        )

    dissolved = unary_union(polygons)
    if dissolved.is_empty or not dissolved.is_valid:
        raise HourlyThermalPilotRegistryError(
            "dissolved Phoenix provider AOI is invalid"
        )
    if isinstance(dissolved, Polygon):
        provider_aoi: dict[str, Any] = {
            "type": "Polygon",
            "coordinates": _canonical_polygon(dissolved),
        }
    elif isinstance(dissolved, MultiPolygon):
        parts = sorted(
            (_canonical_polygon(part) for part in dissolved.geoms),
            key=lambda coords: json.dumps(coords, separators=(",", ":")),
        )
        provider_aoi = {"type": "MultiPolygon", "coordinates": parts}
    else:
        raise HourlyThermalPilotRegistryError(
            f"dissolved Phoenix provider AOI has unsupported type {dissolved.geom_type}"
        )
    if len(plan_partitions(provider_aoi)) != 1:
        raise HourlyThermalPilotRegistryError(
            "Phoenix pilot AOI must remain one partition"
        )
    return provider_aoi


def render_phoenix_hourly_pilot_provider_aoi(root: Path) -> bytes:
    return (
        json.dumps(
            build_phoenix_hourly_pilot_provider_aoi(root),
            indent=2,
            sort_keys=True,
        )
        + "\n"
    ).encode("utf-8")


def _source(root: Path, relative: Path, role: str) -> HourlyPilotSource:
    return HourlyPilotSource(
        role=role,
        path=relative.as_posix(),
        sha256=_sha256(_bytes(root, relative)),
    )


def build_phoenix_hourly_thermal_pilot_manifest(
    root: Path,
) -> HourlyThermalPilotManifest:
    repo = Path(root).resolve()
    event = load_phoenix_hourly_thermal_event_contract(root=repo)
    coverage = load_phoenix_expected_tile_coverage_evidence(repo)
    config = _json(repo, AREA_CONFIG_RELATIVE_PATH)
    area_manifest = _json(repo, AREA_MANIFEST_RELATIVE_PATH)
    provider_raw = _bytes(repo, PHOENIX_HOURLY_PILOT_PROVIDER_AOI_RELATIVE_PATH)
    provider_expected = render_phoenix_hourly_pilot_provider_aoi(repo)
    if provider_raw != provider_expected:
        raise HourlyThermalPilotRegistryError(
            "tracked hourly pilot provider AOI differs from the frozen tract dissolve"
        )
    provider_aoi = json.loads(provider_raw.decode("utf-8"))

    if (
        config.get("area_id") != AREA_ID
        or _sha256(_bytes(repo, AREA_CONFIG_RELATIVE_PATH)) != FROZEN_AREA_CONFIG_SHA256
        or config.get("granularity_m") != GRANULARITY_M
        or config.get("partition_strategy") != PARTITION_STRATEGY
        or area_manifest.get("area_config_sha256") != FROZEN_AREA_CONFIG_SHA256
        or area_manifest.get("geometry_sha256") != coverage.evidence.geometry_sha256
    ):
        raise HourlyThermalPilotRegistryError(
            "Phoenix frozen area inputs do not match the pilot contract"
        )
    if event.contract.coverage.temporal_mode != "single_hour":
        raise HourlyThermalPilotRegistryError(
            "hourly event candidate is not single-hour"
        )

    slots: list[HourlyPilotSlot] = []
    ordinal = 0
    for day in PILOT_DATES:
        for hour in PILOT_HOURS:
            ordinal += 1
            request = HeatmapFetchRequest(
                polygon_aoi=provider_aoi,
                start_date=day,
                start_time=hour,
                temporal_mode=HeatmapTemporalMode.SINGLE_HOUR,
                granularity=GRANULARITY_M,
                analytic_type="tcm",
                data_mode=DataMode.LIVE,
            )
            slot_id = f"{day}T{hour}"
            slots.append(
                HourlyPilotSlot(
                    ordinal=ordinal,
                    slot_id=slot_id,
                    date_local=day,
                    time_local=hour,
                    phase="canary" if slot_id == CANARY_SLOT_ID else "batch",
                    request_fingerprint=heatmap_fingerprint(request),
                )
            )

    return HourlyThermalPilotManifest(
        schema_version="PHX_HOURLY_THERMAL_PILOT_MANIFEST_V1",
        manifest_version="PHX_HOURLY_TYPE1_PILOT_V1",
        status="PREREGISTERED",
        area_id=AREA_ID,
        iana_timezone="America/Phoenix",
        purpose=(
            "provider_request_semantics",
            "cache_and_debit_observability",
            "hourly_zone_coverage",
            "aligned_tile_field_retention",
        ),
        pilot_dates_local=PILOT_DATES,
        pilot_hours_local=PILOT_HOURS,
        request_count=72,
        request_contract=HourlyPilotRequestContract(
            endpoint="/v1/heatmap",
            analytic_type="tcm",
            temporal_mode="single_hour",
            filter_type=1,
            observation_kind="instant",
            upstream_time_semantics="aoi_local_time",
            granularity_m=100,
            partition_strategy="single_aoi",
            expected_partition_count=1,
            window_aggregates_allowed=False,
            interpolation_allowed=False,
        ),
        quality_gates=HourlyPilotQualityGates(
            expected_field_tile_count=3749,
            expected_zone_count=25,
            exact_zone_tile_counts_required=True,
            every_tile_requires_temperature=True,
            every_zone_requires_temperature=True,
            complete_assembly_required=True,
            cache_recheck_required=True,
            exact_debit_metering_required_for_live_request=True,
            stop_on_first_failed_slot=True,
            automatic_retry_allowed=False,
            aligned_raw_tile_retention_required=True,
            canary=HourlyPilotCanaryGate(
                slot_id=CANARY_SLOT_ID,
                reference_path=CANARY_REFERENCE_RELATIVE_PATH.as_posix(),
                reference_local_time=CANARY_SLOT_ID,
                required_reference_zone_count=25,
                maximum_mean_absolute_delta_c=0.02,
                maximum_zone_absolute_delta_c=0.05,
                purpose="same_instant_request_and_aggregation_consistency",
            ),
        ),
        execution_boundary=HourlyPilotExecutionBoundary(
            canary_must_pass_before_batch=True,
            maximum_manifest_slots=72,
            maximum_new_vendor_requests=72,
            credit_cap=None,
            scope_is_request_count_not_budget=True,
            api_key_may_be_persisted=False,
            hosted_live_may_be_enabled=False,
            public_route_may_be_added=False,
        ),
        claim_boundaries=HourlyPilotClaimBoundaries(
            closes_gate0=False,
            freezes_hourly_event=False,
            authorizes_probability=False,
            authorizes_forecast=False,
            authorizes_operational_outcome=False,
            authorizes_health_outcome=False,
            authorizes_priority_or_intervention=False,
        ),
        sources=[
            _source(
                repo,
                PHOENIX_HOURLY_EVENT_CONTRACT_RELATIVE_PATH,
                "hourly_event_candidate",
            ),
            _source(repo, AREA_CONFIG_RELATIVE_PATH, "area_config"),
            _source(repo, AREA_MANIFEST_RELATIVE_PATH, "area_manifest"),
            _source(repo, ZONE_GEOMETRY_RELATIVE_PATH, "zone_geometry"),
            _source(
                repo, PHOENIX_HOURLY_PILOT_PROVIDER_AOI_RELATIVE_PATH, "provider_aoi"
            ),
            _source(
                repo, PHOENIX_COVERAGE_EVIDENCE_RELATIVE_PATH, "expected_tile_coverage"
            ),
            _source(repo, CANARY_REFERENCE_RELATIVE_PATH, "canary_reference_panel"),
        ],
        slots=slots,
    )


def render_phoenix_hourly_thermal_pilot_manifest(
    manifest: HourlyThermalPilotManifest,
) -> bytes:
    return (json.dumps(manifest.model_dump(mode="json"), indent=2) + "\n").encode(
        "utf-8"
    )


def load_phoenix_hourly_thermal_pilot_manifest(
    *,
    root: Path | None = None,
    expected_sha256: str | None = None,
) -> ResolvedHourlyThermalPilotManifest:
    repo = Path(root).resolve() if root is not None else hackathon_root()
    path = _path(repo, PHOENIX_HOURLY_PILOT_MANIFEST_RELATIVE_PATH)
    raw = path.read_bytes()
    digest = _sha256(raw)
    expected = expected_sha256 or PHOENIX_HOURLY_PILOT_MANIFEST_SHA256
    if digest != expected:
        raise HourlyThermalPilotRegistryError(
            "Phoenix hourly pilot manifest SHA-256 mismatch"
        )
    try:
        manifest = HourlyThermalPilotManifest.model_validate_json(raw)
    except ValidationError as exc:
        raise HourlyThermalPilotRegistryError(
            f"invalid Phoenix hourly pilot manifest: {exc}"
        ) from exc
    rebuilt = render_phoenix_hourly_thermal_pilot_manifest(
        build_phoenix_hourly_thermal_pilot_manifest(repo)
    )
    if rebuilt != raw:
        raise HourlyThermalPilotRegistryError(
            "Phoenix hourly pilot manifest differs from deterministic rebuild"
        )
    return ResolvedHourlyThermalPilotManifest(
        manifest=manifest,
        path=path,
        sha256=digest,
        provider_aoi=_json(repo, PHOENIX_HOURLY_PILOT_PROVIDER_AOI_RELATIVE_PATH),
    )


def request_for_hourly_pilot_slot(
    resolved: ResolvedHourlyThermalPilotManifest,
    slot: HourlyPilotSlot,
) -> HeatmapFetchRequest:
    request = HeatmapFetchRequest(
        polygon_aoi=resolved.provider_aoi,
        start_date=slot.date_local,
        start_time=slot.time_local,
        temporal_mode=HeatmapTemporalMode.SINGLE_HOUR,
        granularity=resolved.manifest.request_contract.granularity_m,
        analytic_type="tcm",
        data_mode=DataMode.LIVE,
    )
    if heatmap_fingerprint(request) != slot.request_fingerprint:
        raise HourlyThermalPilotRegistryError(
            f"hourly pilot request fingerprint drift for {slot.slot_id}"
        )
    return request
