"""Gated demo temporal GETs. Cache only. No acquire."""

from fastapi.testclient import TestClient

from app.main import app as public_app

SEED = "04013107401"


def test_demo_matched_window_is_compact_and_read_only() -> None:
    response = TestClient(public_app).get(
        "/api/v1/demo/matched-nighttime-window",
        params={"area_id": "phoenix-demo", "geoid": SEED},
    )
    assert response.status_code == 200
    body = response.json()
    assert body["window_label"] == "MATCHED SUMMER NIGHTTIME WINDOW"
    assert body["selected_area"]["matched_nights"] == 31
    assert "spend" not in body
    assert "acquire" not in body
    assert "observations" not in body
    assert "q_A" not in str(body["selected_area"])


def test_demo_observed_instants_bind_p14_activity_ids() -> None:
    response = TestClient(public_app).get(
        "/api/v1/demo/observed-thermal-instants",
        params={"area_id": "phoenix-demo", "geoid": SEED},
    )
    assert response.status_code == 200
    body = response.json()
    ids = [item["instant_id"] for item in body["observations"]]
    assert ids == ["03:00_D", "15:00", "21:00", "03:00_D+1"]
    by_id = {item["instant_id"]: item for item in body["observations"]}
    assert by_id["15:00"]["activity_id"] == "92086c4c-1550-4263-8ac8-9a6c9e030bc4"
    assert by_id["21:00"]["activity_id"] == "9865bd33-43a0-42b0-bc9b-74b27510002d"
    assert all("q_A" not in item for item in body["observations"])
