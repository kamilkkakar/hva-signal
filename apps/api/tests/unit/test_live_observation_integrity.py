import json
from datetime import datetime
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from app.api.routes import bounded_selected_time_live as route
from app.core.config import get_settings
from app.domain.multicity.type1_live import Type1LiveClientRequest, seed_type1_live_cache
from app.integrations.fortyguard.cache import FortyGuardCache
from app.main import app

FIXTURE = Path(__file__).resolve().parents[1] / "fixtures/live/phoenix_2021_empty_response.json"


@pytest.fixture
def captured():
    return json.loads(FIXTURE.read_text())


@pytest.fixture
def client(monkeypatch, tmp_path, captured):
    monkeypatch.setenv("BOUNDED_SELECTED_TIME_LIVE_ENABLED", "true")
    monkeypatch.setenv("CACHE_DIR", str(tmp_path))
    get_settings.cache_clear()
    route._daily_counts.clear()
    seed_type1_live_cache(
        Type1LiveClientRequest(city="Phoenix", target_local=datetime(2021, 8, 14, 15)),
        payload=captured["result"]["payload"],
        cache=FortyGuardCache(tmp_path),
    )
    # A retained failed acquisition must never automatically become a new purchase.
    import app.domain.multicity.type1_live as type1
    def refuse(*args, **kwargs):
        pytest.fail("metadata-only cache must be reconciled, not reacquired")
    monkeypatch.setattr(type1, "_bounded_selected_time_acquire", refuse)
    with TestClient(app) as api:
        yield api
    get_settings.cache_clear()
    route._daily_counts.clear()


def fetch(client):
    response = client.post("/api/v1/live/selected-time", json={
        "city_id": "phoenix", "local_datetime": "2021-08-14T15:00:00",
    })
    assert response.status_code == 200
    return response.json()


def test_actual_2021_empty_result_is_unavailable_without_repurchase(client, captured):
    for _ in range(2):
        result = fetch(client)
        assert result["status"] == "observation_unavailable"
        assert result["observation_status"] == "unavailable"
        assert result["acquisition_status"] == "cache_hit"
        assert result["provenance"]["vendor_attempted"] is False
        assert result["result"]["payload"]["activity_id"] == captured["result"]["payload"]["activity_id"]
        assert result["analysis"]["bindable_temperature_values"] == 0
        assert all(row["temperature_c"] is None for row in result["analysis"]["zones"])
        assert "No usable zone temperatures" in result["message"]


@pytest.mark.parametrize("available", [1, 24, 25])
def test_actual_zone_coverage_controls_result_state(client, captured, monkeypatch, available):
    analysis = captured["analysis"]
    for i, row in enumerate(analysis["zones"]):
        row.update(temperature_c=38.5 if i < available else None,
                   tile_count=1 if i < available else 0,
                   coverage_status="valid" if i < available else "missing")
    analysis.update(bindable_temperature_values=available, source_tile_count=available)
    monkeypatch.setattr(route, "aggregate_cached_live_zones", lambda *args: analysis)
    result = fetch(client)
    assert result["observation_status"] == ("available" if available == 25 else "partial")
    assert result["status"] == ("cache_hit" if available == 25 else "partial_observation")
    assert result["analysis"]["bindable_temperature_values"] == available
    assert sum(row["temperature_c"] is not None for row in result["analysis"]["zones"]) == available


@pytest.mark.parametrize("field,value", [
    ("city", "Tucson"), ("local_datetime", "2024-07-08T15:00:00"),
    ("timezone", "UTC"), ("bindable_temperature_values", 25),
])
def test_mismatched_identity_or_counts_cannot_be_available(client, captured, monkeypatch, field, value):
    analysis = captured["analysis"]
    analysis["zones"][0].update(temperature_c=38.5, tile_count=1, coverage_status="valid")
    analysis.update(bindable_temperature_values=1, source_tile_count=1)
    analysis[field] = value
    monkeypatch.setattr(route, "aggregate_cached_live_zones", lambda *args: analysis)
    assert fetch(client)["status"] == "observation_unavailable"


def test_mapping_exception_keeps_acquisition_record_but_withholds_observation(client, monkeypatch):
    def broken(*args):
        raise ValueError("private provider diagnostic")
    monkeypatch.setattr(route, "aggregate_cached_live_zones", broken)
    result = fetch(client)
    assert result["status"] == "observation_unavailable"
    assert result["result"]["payload"]["activity_id"]
    assert "private provider diagnostic" not in json.dumps(result)
