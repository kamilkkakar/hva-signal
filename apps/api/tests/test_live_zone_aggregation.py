from __future__ import annotations

from types import SimpleNamespace

from shapely.geometry import box, mapping

from app.domain.multicity import live_zone_aggregation as aggregation


def _tile(x: float, y: float, value: float):
    geometry = mapping(box(x - 0.1, y - 0.1, x + 0.1, y + 0.1))
    observation = SimpleNamespace(statistic="instant", value=value)
    return SimpleNamespace(geometry=geometry, observations=[observation])


def test_live_tiles_aggregate_to_zone_means_without_imputation(monkeypatch):
    monkeypatch.setattr(
        aggregation,
        "resolve_city_aoi",
        lambda _city: SimpleNamespace(city="Phoenix", timezone="America/Phoenix"),
    )
    monkeypatch.setattr(
        aggregation,
        "_zones",
        lambda _city: [
            ("00000000001", box(0, 0, 1, 1)),
            ("00000000002", box(1, 0, 2, 1)),
            ("00000000003", box(2, 0, 3, 1)),
        ],
    )
    monkeypatch.setattr(
        aggregation,
        "_vendor_tiles",
        lambda _city, _clock, _settings: [
            _tile(0.25, 0.25, 30.0),
            _tile(0.75, 0.75, 32.0),
            _tile(1.5, 0.5, 40.0),
        ],
    )

    from datetime import datetime

    result = aggregation.aggregate_cached_live_zones(
        "Phoenix",
        datetime(2026, 9, 1, 15, 0, 0),
        object(),  # cache access is patched out in this unit test
    )

    assert result["geometry_zone_count"] == 3
    assert result["bindable_temperature_values"] == 2
    assert result["source_tile_count"] == 3
    assert result["aggregation_contract"] == (
        "HVA_NATIONAL_THERMAL_AGGREGATION_V1_CENTROID_WITHIN_MEAN"
    )
    assert result["zones"][0] == {
        "zone_id": "00000000001",
        "temperature_c": 31.0,
        "tile_count": 2,
        "coverage_status": "valid",
    }
    assert result["zones"][1]["temperature_c"] == 40.0
    assert result["zones"][2] == {
        "zone_id": "00000000003",
        "temperature_c": None,
        "tile_count": 0,
        "coverage_status": "missing",
    }
