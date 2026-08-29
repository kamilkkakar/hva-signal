"""Unit tests for tile→zone aggregation (centroid-within + mean)."""

from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path

import pytest

FIXTURES = Path(__file__).resolve().parent.parent / "fixtures" / "zones"


def _load(name: str) -> dict:
    return json.loads((FIXTURES / name).read_text(encoding="utf-8"))


def _default_spec(minimum_coverage_ratio: float = 0.5):
    from app.services.zone_aggregator import ThermalAggregationSpec

    return ThermalAggregationSpec(
        version="test-v1",
        assignment_method="centroid_within",
        statistic="mean",
        minimum_coverage_ratio=minimum_coverage_ratio,
        zero_tile_behavior="insufficient_evidence",
        boundary_behavior="strict",
        notes=[],
    )


def _aggregate(
    zones: dict,
    tiles: dict,
    *,
    expected_tile_counts: dict[str, float],
    minimum_coverage_ratio: float = 0.5,
):
    from app.services.zone_aggregator import aggregate_tiles_to_zones

    return aggregate_tiles_to_zones(
        zones_geojson=zones,
        tiles_geojson=tiles,
        spec=_default_spec(minimum_coverage_ratio),
        expected_tile_counts=expected_tile_counts,
        valid_time=datetime(2024, 7, 15, 15, 0, tzinfo=timezone.utc),
        resolution_m=100,
    )


def test_centroid_within_assigns_tiles_to_matching_zones() -> None:
    from app.services.zone_aggregator import assign_tiles_centroid_within

    zones = _load("synthetic_zones.geojson")
    tiles = _load("synthetic_tiles.geojson")

    assignments = assign_tiles_centroid_within(zones, tiles)

    assert {tile["properties"]["tile_id"] for tile in assignments["zone_a"]} == {
        "tile_a1",
        "tile_a2",
    }
    assert {tile["properties"]["tile_id"] for tile in assignments["zone_b"]} == {"tile_b1"}
    assert assignments.get("unassigned", []) == [
        next(
            feature
            for feature in tiles["features"]
            if feature["properties"]["tile_id"] == "tile_outside"
        )
    ]


def test_mean_aggregation_averages_assigned_tile_temperatures() -> None:
    zones = _load("synthetic_zones.geojson")
    tiles = _load("synthetic_tiles.geojson")

    outcomes = _aggregate(
        zones,
        tiles,
        expected_tile_counts={"zone_a": 2.0, "zone_b": 1.0},
        minimum_coverage_ratio=0.5,
    )
    by_zone = {outcome.series.zone_id: outcome for outcome in outcomes}

    zone_a = by_zone["zone_a"]
    assert zone_a.series.tile_count == 2
    assert zone_a.ranked is True
    assert zone_a.result_status == "ok"
    assert zone_a.series.observations[0].value == pytest.approx(32.0)
    assert zone_a.series.observations[0].statistic == "mean"
    assert zone_a.series.temporal_mode == "single_hour"
    assert zone_a.series.source == "replay"
    assert zone_a.series.upstream_time_semantics == "aoi_local_time"

    zone_b = by_zone["zone_b"]
    assert zone_b.series.observations[0].value == pytest.approx(40.0)


def test_zero_assigned_tiles_is_insufficient_evidence_not_zero() -> None:
    zones = _load("synthetic_zones.geojson")
    tiles = {"type": "FeatureCollection", "features": []}

    outcomes = _aggregate(
        zones,
        tiles,
        expected_tile_counts={"zone_a": 4.0, "zone_b": 4.0},
    )
    zone_a = next(o for o in outcomes if o.series.zone_id == "zone_a")

    assert zone_a.series.tile_count == 0
    assert zone_a.result_status == "insufficient_evidence"
    assert "insufficient_evidence" in zone_a.series.quality_flags
    assert zone_a.series.observations[0].value is None
    assert zone_a.series.observations[0].value != 0
    assert zone_a.ranked is False


def test_tile_coverage_ratio_is_assigned_over_expected() -> None:
    zones = _load("synthetic_zones.geojson")
    tiles = _load("sparse_tiles.geojson")

    outcomes = _aggregate(
        zones,
        tiles,
        expected_tile_counts={"zone_a": 4.0, "zone_b": 1.0},
        minimum_coverage_ratio=0.25,
    )
    zone_a = next(o for o in outcomes if o.series.zone_id == "zone_a")

    assert zone_a.series.tile_count == 2
    assert zone_a.series.expected_tile_count == 4.0
    assert zone_a.series.tile_coverage_ratio == pytest.approx(0.5)


def test_below_coverage_floor_is_ranked_false_and_insufficient() -> None:
    zones = _load("synthetic_zones.geojson")
    tiles = _load("sparse_tiles.geojson")

    outcomes = _aggregate(
        zones,
        tiles,
        expected_tile_counts={"zone_a": 4.0, "zone_b": 1.0},
        minimum_coverage_ratio=0.8,
    )
    zone_a = next(o for o in outcomes if o.series.zone_id == "zone_a")

    assert zone_a.series.tile_coverage_ratio == pytest.approx(0.5)
    assert zone_a.ranked is False
    assert zone_a.result_status == "insufficient_evidence"
    assert "insufficient_evidence" in zone_a.series.quality_flags


def test_above_coverage_floor_is_ranked_true() -> None:
    zones = _load("synthetic_zones.geojson")
    tiles = _load("synthetic_tiles.geojson")

    outcomes = _aggregate(
        zones,
        tiles,
        expected_tile_counts={"zone_a": 2.0, "zone_b": 1.0},
        minimum_coverage_ratio=0.5,
    )
    zone_a = next(o for o in outcomes if o.series.zone_id == "zone_a")

    assert zone_a.series.tile_coverage_ratio == pytest.approx(1.0)
    assert zone_a.ranked is True
    assert zone_a.result_status == "ok"


def test_does_not_interpolate_missing_tiles() -> None:
    zones = _load("synthetic_zones.geojson")
    tiles = _load("sparse_tiles.geojson")

    outcomes = _aggregate(
        zones,
        tiles,
        expected_tile_counts={"zone_a": 4.0, "zone_b": 1.0},
        minimum_coverage_ratio=0.25,
    )
    zone_a = next(o for o in outcomes if o.series.zone_id == "zone_a")

    # Mean of 10 and 20 only — not diluted toward an interpolated fourth tile.
    assert zone_a.series.observations[0].value == pytest.approx(15.0)


def test_assigned_tiles_without_temperature_are_insufficient_not_ok() -> None:
    zones = _load("synthetic_zones.geojson")
    tiles = _load("synthetic_tiles.geojson")
    for feature in tiles["features"]:
        feature["properties"]["average_temperature"] = None

    outcomes = _aggregate(
        zones,
        tiles,
        expected_tile_counts={"zone_a": 2.0, "zone_b": 1.0},
    )
    zone_a = next(o for o in outcomes if o.series.zone_id == "zone_a")

    assert zone_a.series.tile_count == 2
    assert zone_a.series.observations[0].value is None
    assert zone_a.result_status == "insufficient_evidence"
    assert zone_a.ranked is False
    assert "insufficient_evidence" in zone_a.series.quality_flags


def test_partial_missing_temperatures_are_flagged_and_not_imputed() -> None:
    zones = _load("synthetic_zones.geojson")
    tiles = _load("synthetic_tiles.geojson")
    for feature in tiles["features"]:
        if feature["properties"]["tile_id"] == "tile_a2":
            feature["properties"]["average_temperature"] = None

    outcomes = _aggregate(
        zones,
        tiles,
        expected_tile_counts={"zone_a": 2.0, "zone_b": 1.0},
    )
    zone_a = next(o for o in outcomes if o.series.zone_id == "zone_a")

    assert zone_a.series.observations[0].value == pytest.approx(30.0)
    assert "missing_tile_temperature" in zone_a.series.quality_flags


def test_uses_mean_not_max_or_p90() -> None:
    from app.services.zone_aggregator import aggregate_mean_temperature

    values = [10.0, 20.0, 50.0]
    assert aggregate_mean_temperature(values) == pytest.approx(80.0 / 3.0)
    assert aggregate_mean_temperature(values) != max(values)

    zones = _load("synthetic_zones.geojson")
    tiles = _load("synthetic_tiles.geojson")
    outcomes = _aggregate(
        zones,
        tiles,
        expected_tile_counts={"zone_a": 2.0, "zone_b": 1.0},
    )
    zone_a = next(o for o in outcomes if o.series.zone_id == "zone_a")
    assert zone_a.series.observations[0].statistic == "mean"
    assert zone_a.series.observations[0].value == pytest.approx(32.0)
    assert zone_a.series.observations[0].value != 34.0
