"""Cross-origin geometry identity headers must be readable by the web client."""

from fastapi.testclient import TestClient

from app.main import GEOMETRY_CORS_EXPOSE_HEADERS, app


def test_geometry_response_exposes_identity_headers_to_loopback_origin() -> None:
    client = TestClient(app)
    response = client.get(
        "/api/v1/areas/phoenix-demo/geometry",
        headers={"Origin": "http://127.0.0.1:14191"},
    )
    assert response.status_code == 200
    exposed = response.headers.get("access-control-expose-headers", "").lower()
    for name in GEOMETRY_CORS_EXPOSE_HEADERS:
        assert name.lower() in exposed
        assert response.headers.get(name)
    assert response.headers.get("access-control-allow-origin") == "http://127.0.0.1:14191"


def test_analysis_job_post_allows_loopback_preview_origin() -> None:
    client = TestClient(app)
    response = client.post(
        "/api/v1/analysis/jobs",
        headers={"Origin": "http://127.0.0.1:14191"},
        json={
            "area_id": "phoenix-demo",
            "analysis_time": "2022-07-01T03:00:00",
            "analysis_mode": "retrospective",
            "horizon_hours": 12,
            "lookback_hours": 0,
            "granularity_m": 100,
            "data_mode": "replay",
        },
    )
    assert response.status_code == 202
    assert response.headers.get("access-control-allow-origin") == "http://127.0.0.1:14191"
    assert response.json().get("job_id")
