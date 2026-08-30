"""Compact MatchedNighttimeWindowView. Unpublished GET. No acquire."""

from __future__ import annotations

import json

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient

from app.domain.matched_nighttime_window import api_contract
from app.main import app as public_app
from app.services.matched_nighttime_window import assemble_matched_nighttime_window_view

SEED = "04013107401"


def _client() -> TestClient:
    from app.api.routes.matched_nighttime_window import router

    application = FastAPI()
    application.include_router(router)
    return TestClient(application)


def test_api_contract_stays_unpublished() -> None:
    contract = api_contract()
    assert contract["unpublished"] is True
    assert contract["not_signal_a"] is True
    assert contract["window_label"] == "MATCHED SUMMER NIGHTTIME WINDOW"


def test_public_app_does_not_mount_matched_window_get() -> None:
    client = TestClient(public_app)
    response = client.get(
        "/internal/v1/matched-nighttime-window",
        params={"geoid": SEED},
    )
    assert response.status_code == 404


def test_compact_view_has_required_fields_not_the_panel() -> None:
    view = assemble_matched_nighttime_window_view(SEED)
    assert view["window_label"] == "MATCHED SUMMER NIGHTTIME WINDOW"
    assert view["window_start"] == "06-30"
    assert view["window_end"] == "07-30"
    assert view["window_dates"] == "30 Jun-30 Jul"
    assert view["local_time"] == "03:00"
    assert view["years"] == [2022, 2023, 2024]
    selected = view["selected_area"]
    assert selected["area_id"] == "phoenix-demo"
    assert selected["geoid"] == SEED
    assert set(selected["mean_by_year"]) == {"2022", "2023", "2024"}
    assert selected["change_2024_vs_2022"] == pytest.approx(1.54, abs=0.05)
    assert selected["matched_nights_warmer"] == 22
    assert selected["matched_nights_cooler"] >= 0
    assert view["analysis_geography"]["median_change_2024_vs_2022"] == pytest.approx(
        1.53, abs=0.05
    )
    assert view["source"] == "FortyGuard"
    assert view["method"] == "matched same-calendar dates / same local hour"
    blob = json.dumps(view)
    assert "observations" not in view
    assert "2325" not in blob
    assert "JJA" not in blob
    assert "HeatDose" not in blob
    assert "climate" not in blob.lower()
    assert "q_A" not in blob


def test_internal_get_is_read_only_and_compact() -> None:
    response = _client().get(
        "/internal/v1/matched-nighttime-window",
        params={"area_id": "phoenix-demo", "geoid": SEED},
    )
    assert response.status_code == 200
    body = response.json()
    assert body["unpublished"] is True
    assert body["not_signal_a"] is True
    assert "spend" not in body
    assert "acquire" not in body
    assert "activity_id" not in body
    assert len(json.dumps(body)) < 2000
