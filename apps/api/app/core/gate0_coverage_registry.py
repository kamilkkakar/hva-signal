"""Build and load the tracked Phoenix expected-tile-coverage evidence."""

from __future__ import annotations

import hashlib
import json
import statistics
from collections import defaultdict
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from pydantic import ValidationError

from app.domain.gate0_coverage import (
    Gate0CoverageDistribution,
    Gate0CoveragePolicyBoundary,
    Gate0CoverageSource,
    Gate0ExpectedTileCoverageEvidence,
    Gate0ZoneExpectedTileCount,
)

PHOENIX_COVERAGE_EVIDENCE_RELATIVE_PATH = (
    Path("data") / "gate0" / "phoenix-v1" / "expected_tile_coverage.json"
)
PHOENIX_COVERAGE_EVIDENCE_SHA256 = (
    "23004b6ed1b52d5e6f6309c1b9c1f2a8b6e3a27ee00e386f655bde50ac8e2d4f"
)
PHOENIX_COVERAGE_GENERATOR_RELATIVE_PATH = (
    Path("scripts") / "build_gate0_expected_tile_coverage.py"
)

AREA_CONFIG = Path("data") / "demo" / "phoenix" / "area_config.json"
AREA_MANIFEST = Path("data") / "areas" / "phoenix-demo" / "manifest.json"
ZONE_GEOMETRY = Path("data") / "areas" / "phoenix-demo" / "geometry.geojson"
REFERENCE_PANEL = Path("data") / "phoenix" / "reference" / "observations.jsonl"
SELECTED_TIME_SNAPSHOTS = (
    Path("data") / "phoenix" / "snapshots" / "2024-07-08T15-00.snapshot.json",
    Path("data") / "phoenix" / "snapshots" / "2024-07-08T21-00.snapshot.json",
)


class Gate0CoverageRegistryError(ValueError):
    """Coverage evidence is missing, stale, malformed, or internally inconsistent."""


@dataclass(frozen=True)
class ResolvedGate0CoverageEvidence:
    evidence: Gate0ExpectedTileCoverageEvidence
    path: Path
    sha256: str


def _path(root: Path, relative: Path) -> Path:
    candidate = (root / relative).resolve()
    try:
        candidate.relative_to(root.resolve())
    except ValueError as exc:
        raise Gate0CoverageRegistryError(
            f"coverage evidence path escapes repository root: {relative.as_posix()}"
        ) from exc
    if not candidate.is_file():
        raise Gate0CoverageRegistryError(
            f"coverage evidence source is missing: {relative.as_posix()}"
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
        raise Gate0CoverageRegistryError(
            f"coverage evidence source is malformed: {relative.as_posix()}"
        ) from exc
    if not isinstance(value, dict):
        raise Gate0CoverageRegistryError(
            f"coverage evidence source must be an object: {relative.as_posix()}"
        )
    return value


def _source(
    root: Path,
    relative: Path,
    *,
    role: str,
    field_count: int = 0,
    zone_row_count: int = 0,
) -> Gate0CoverageSource:
    return Gate0CoverageSource(
        role=role,
        path=relative.as_posix(),
        sha256=_sha256(_bytes(root, relative)),
        observed_field_count=field_count,
        observed_zone_row_count=zone_row_count,
    )


def _geometry_zone_ids(root: Path, expected_count: int) -> tuple[str, ...]:
    document = _json(root, ZONE_GEOMETRY)
    features = document.get("features")
    if document.get("type") != "FeatureCollection" or not isinstance(features, list):
        raise Gate0CoverageRegistryError("Phoenix geometry is not a FeatureCollection")
    zone_ids: list[str] = []
    for feature in features:
        if not isinstance(feature, dict):
            raise Gate0CoverageRegistryError("Phoenix geometry contains an invalid feature")
        properties = feature.get("properties")
        if not isinstance(properties, dict) or not properties.get("GEOID"):
            raise Gate0CoverageRegistryError("Phoenix geometry feature is missing GEOID")
        zone_ids.append(str(properties["GEOID"]).zfill(11))
    if len(zone_ids) != expected_count or len(zone_ids) != len(set(zone_ids)):
        raise Gate0CoverageRegistryError(
            "Phoenix geometry does not contain the expected unique zone set"
        )
    return tuple(sorted(zone_ids))


def _reference_fields(
    root: Path,
    expected_zone_ids: tuple[str, ...],
) -> dict[str, dict[str, int]]:
    raw = _bytes(root, REFERENCE_PANEL)
    fields: dict[str, dict[str, int]] = defaultdict(dict)
    try:
        lines = raw.decode("utf-8").splitlines()
        rows = [json.loads(line) for line in lines if line.strip()]
    except (UnicodeDecodeError, json.JSONDecodeError) as exc:
        raise Gate0CoverageRegistryError("Phoenix reference panel is malformed") from exc
    for row in rows:
        if not isinstance(row, dict):
            raise Gate0CoverageRegistryError("Phoenix reference row must be an object")
        if row.get("usable") is not True or row.get("mean_tcm_c") is None:
            raise Gate0CoverageRegistryError(
                "coverage baseline requires complete usable reference observations"
            )
        field_id = f"{row.get('date')}T{row.get('local_time')}"
        zone_id = str(row.get("geoid") or "").zfill(11)
        raw_count = row.get("contributing_tiles")
        if isinstance(raw_count, bool) or not isinstance(raw_count, int) or raw_count <= 0:
            raise Gate0CoverageRegistryError(
                "reference contributing_tiles must be a positive integer"
            )
        if zone_id in fields[field_id]:
            raise Gate0CoverageRegistryError(
                f"duplicate reference coverage row for {field_id} {zone_id}"
            )
        fields[field_id][zone_id] = raw_count
    if not fields:
        raise Gate0CoverageRegistryError("Phoenix reference panel contains no fields")
    expected = set(expected_zone_ids)
    if any(set(counts) != expected for counts in fields.values()):
        raise Gate0CoverageRegistryError(
            "every reference field must contain the complete Phoenix zone set"
        )
    return dict(fields)


def _snapshot_field(
    root: Path,
    relative: Path,
    *,
    expected_zone_ids: tuple[str, ...],
    geometry_sha256: str,
) -> dict[str, int]:
    document = _json(root, relative)
    if (
        document.get("area_id") != "phoenix-demo"
        or document.get("availability") != "READY"
        or document.get("geometry_sha256") != geometry_sha256
        or document.get("expected_zone_count") != len(expected_zone_ids)
        or document.get("valid_zone_count") != len(expected_zone_ids)
        or document.get("missing_zone_ids") != []
    ):
        raise Gate0CoverageRegistryError(
            f"snapshot is not a complete matching Phoenix field: {relative.as_posix()}"
        )
    counts: dict[str, int] = {}
    zones = document.get("zones")
    if not isinstance(zones, list):
        raise Gate0CoverageRegistryError("snapshot zones must be a list")
    for zone in zones:
        if not isinstance(zone, dict):
            raise Gate0CoverageRegistryError("snapshot zone must be an object")
        zone_id = str(zone.get("zone_id") or "").zfill(11)
        raw_count = zone.get("tile_count")
        if isinstance(raw_count, bool) or not isinstance(raw_count, int) or raw_count <= 0:
            raise Gate0CoverageRegistryError("snapshot tile_count must be a positive integer")
        if zone_id in counts:
            raise Gate0CoverageRegistryError(f"snapshot contains duplicate zone {zone_id}")
        counts[zone_id] = raw_count
    if set(counts) != set(expected_zone_ids):
        raise Gate0CoverageRegistryError("snapshot does not contain the complete Phoenix zone set")
    if document.get("mapped_tile_count") != sum(counts.values()):
        raise Gate0CoverageRegistryError("snapshot mapped_tile_count does not equal its zone sum")
    return counts


def build_phoenix_expected_tile_coverage_evidence(
    root: Path,
) -> Gate0ExpectedTileCoverageEvidence:
    """Derive the baseline from complete tracked fields; reject any inconsistency."""

    repo = Path(root).resolve()
    config = _json(repo, AREA_CONFIG)
    manifest = _json(repo, AREA_MANIFEST)
    config_raw = _bytes(repo, AREA_CONFIG)
    geometry_raw = _bytes(repo, ZONE_GEOMETRY)
    config_sha256 = _sha256(config_raw)
    geometry_sha256 = _sha256(geometry_raw)

    if (
        config.get("area_id") != "phoenix-demo"
        or config.get("version") != "PHX_AREA_CONFIG_V1"
        or config.get("expected_zone_count") != 25
        or config.get("granularity_m") != 100
        or (config.get("thermal_aggregation") or {}).get("assignment_method")
        != "centroid_within"
        or (config.get("thermal_aggregation") or {}).get("statistic") != "mean"
    ):
        raise Gate0CoverageRegistryError(
            "Phoenix AreaConfig does not match the coverage-evidence contract"
        )
    if (
        manifest.get("area_id") != "phoenix-demo"
        or manifest.get("area_config_sha256") != config_sha256
        or manifest.get("geometry_sha256") != geometry_sha256
        or manifest.get("reference_sha256") != _sha256(_bytes(repo, REFERENCE_PANEL))
    ):
        raise Gate0CoverageRegistryError(
            "Phoenix manifest hashes do not match the tracked coverage sources"
        )

    expected_zone_ids = _geometry_zone_ids(repo, 25)
    reference_fields = _reference_fields(repo, expected_zone_ids)
    all_fields: dict[str, dict[str, int]] = dict(reference_fields)
    snapshot_sources: list[Gate0CoverageSource] = []
    for relative in SELECTED_TIME_SNAPSHOTS:
        counts = _snapshot_field(
            repo,
            relative,
            expected_zone_ids=expected_zone_ids,
            geometry_sha256=geometry_sha256,
        )
        snapshot = _json(repo, relative)
        field_id = str(snapshot.get("target_timestamp_local") or relative.stem)
        if field_id in all_fields:
            raise Gate0CoverageRegistryError(f"duplicate observed field {field_id}")
        all_fields[field_id] = counts
        snapshot_sources.append(
            _source(
                repo,
                relative,
                role="selected_time_snapshot",
                field_count=1,
                zone_row_count=len(counts),
            )
        )

    by_zone: dict[str, list[int]] = {zone_id: [] for zone_id in expected_zone_ids}
    field_totals: list[int] = []
    for counts in all_fields.values():
        if set(counts) != set(expected_zone_ids):
            raise Gate0CoverageRegistryError("observed field has a mismatched zone set")
        field_totals.append(sum(counts.values()))
        for zone_id in expected_zone_ids:
            by_zone[zone_id].append(counts[zone_id])
    if len(set(field_totals)) != 1:
        raise Gate0CoverageRegistryError("total mapped tile count changes across fields")
    if any(len(set(counts)) != 1 for counts in by_zone.values()):
        raise Gate0CoverageRegistryError("per-zone mapped tile counts change across fields")

    observed_field_count = len(all_fields)
    zones = [
        Gate0ZoneExpectedTileCount(
            zone_id=zone_id,
            expected_tile_count=counts[0],
            observed_field_count=len(counts),
            minimum_observed_tile_count=min(counts),
            maximum_observed_tile_count=max(counts),
        )
        for zone_id, counts in sorted(by_zone.items())
    ]
    expected_counts = [zone.expected_tile_count for zone in zones]
    sources = [
        _source(repo, AREA_CONFIG, role="area_config"),
        _source(repo, AREA_MANIFEST, role="area_manifest"),
        _source(repo, ZONE_GEOMETRY, role="zone_geometry"),
        _source(
            repo,
            REFERENCE_PANEL,
            role="reference_panel",
            field_count=len(reference_fields),
            zone_row_count=len(reference_fields) * len(expected_zone_ids),
        ),
        *snapshot_sources,
    ]
    return Gate0ExpectedTileCoverageEvidence(
        schema_version="GATE0_EXPECTED_TILE_COVERAGE_V1",
        evidence_version="PHX_EXPECTED_TILE_COVERAGE_V1",
        status="VERIFIED",
        area_id="phoenix-demo",
        generated_by=PHOENIX_COVERAGE_GENERATOR_RELATIVE_PATH.as_posix(),
        geometry_version=str(config["zone_geometry_version"]),
        geometry_sha256=geometry_sha256,
        area_config_version="PHX_AREA_CONFIG_V1",
        area_config_sha256=config_sha256,
        granularity_m=100,
        assignment_method="centroid_within",
        aggregation_statistic="mean",
        expected_zone_count=25,
        reference_field_count=len(reference_fields),
        snapshot_field_count=len(SELECTED_TIME_SNAPSHOTS),
        observed_field_count=observed_field_count,
        observed_zone_row_count=observed_field_count * len(expected_zone_ids),
        all_fields_complete=True,
        counts_invariant_per_zone=True,
        total_count_invariant=True,
        sources=sources,
        distribution=Gate0CoverageDistribution(
            expected_field_tile_count=field_totals[0],
            minimum_zone_tile_count=min(expected_counts),
            median_zone_tile_count=float(statistics.median(expected_counts)),
            maximum_zone_tile_count=max(expected_counts),
            zones=zones,
        ),
        policy_boundary=Gate0CoveragePolicyBoundary(
            zero_tile_behavior="insufficient_evidence",
            minimum_coverage_ratio=None,
            numeric_floor_authorized=False,
            runtime_effect="evidence_baseline_only",
        ),
    )


def render_phoenix_expected_tile_coverage_evidence(
    evidence: Gate0ExpectedTileCoverageEvidence,
) -> bytes:
    payload = evidence.model_dump(mode="json")
    return (json.dumps(payload, indent=2, sort_keys=False) + "\n").encode("utf-8")


def load_phoenix_expected_tile_coverage_evidence(
    root: Path,
    *,
    expected_sha256: str | None = None,
) -> ResolvedGate0CoverageEvidence:
    repo = Path(root).resolve()
    path = _path(repo, PHOENIX_COVERAGE_EVIDENCE_RELATIVE_PATH)
    raw = path.read_bytes()
    digest = _sha256(raw)
    expected = expected_sha256 or PHOENIX_COVERAGE_EVIDENCE_SHA256
    if digest != expected:
        raise Gate0CoverageRegistryError(
            "Phoenix expected-tile-coverage evidence SHA-256 mismatch"
        )
    try:
        evidence = Gate0ExpectedTileCoverageEvidence.model_validate_json(raw)
    except ValidationError as exc:
        raise Gate0CoverageRegistryError(
            f"invalid Phoenix expected-tile-coverage evidence: {exc}"
        ) from exc
    for source in evidence.sources:
        actual = _sha256(_bytes(repo, Path(source.path)))
        if actual != source.sha256:
            raise Gate0CoverageRegistryError(
                f"coverage evidence source SHA-256 mismatch: {source.path}"
            )
    rebuilt = build_phoenix_expected_tile_coverage_evidence(repo)
    if rebuilt != evidence:
        raise Gate0CoverageRegistryError(
            "tracked coverage evidence does not reproduce from its sources"
        )
    return ResolvedGate0CoverageEvidence(
        evidence=evidence,
        path=path,
        sha256=digest,
    )
