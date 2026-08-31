"""Public OpenAPI must not grow a snapshot or prepare surface."""

from app.main import app


def test_public_openapi_has_no_signal_b_or_prepare_paths() -> None:
    schema = app.openapi()
    paths = schema.get("paths") or {}
    assert set(paths) == {
        "/health",
        "/ready",
        "/api/v1/areas",
        "/api/v1/areas/{area_id}/geometry",
        "/api/v1/analysis/jobs",
        "/api/v1/analysis/jobs/{job_id}",
        "/api/v1/cities",
        "/api/v1/cities/{city_id}",
        "/api/v1/cities/{city_id}/capabilities",
        "/api/v1/cross-city/metrics",
        "/api/v1/cross-city/query",
        "/api/v1/cross-city/cities/{city_id}/geometry",
        "/api/v1/areas/{area_id}/context",
        "/api/v1/demo/matched-nighttime-window",
        "/api/v1/demo/observed-thermal-instants",
        "/api/v1/live/selected-time",
    }
    joined = " ".join(paths)
    assert "/api/v1/areas" in paths
    assert "/api/v1/areas/{area_id}/geometry" in paths
    assert "/api/v1/analysis/jobs" in paths
    assert "snapshot" not in joined
    assert "prepare" not in joined
    schemas = schema.get("components", {}).get("schemas", {})
    assert "SelectedTimeSnapshot" not in schemas
    assert "TwoSignalAssembly" not in schemas
    assert "TwoSignalJobState" not in schemas
    assert "TwoSignalPublicJob" not in schemas
    assert "TwoSignalPublicRequest" not in schemas
    assert "SpendGrant" not in schemas
    assert "PublicSelectedTimeResult" not in schemas
    assert "PublicSignalSection" not in schemas
    assert "WorkerHandoff" not in schemas
    assert "DemoAllowancePolicy" not in schemas
    assert "DemoReservation" not in schemas
    assert "HostedDemoResolution" not in schemas
    assert "AcquisitionPreference" not in schemas
    assert "SelectedTimeSnapshotZone" not in schemas
    request_schema = schemas.get("AnalysisRequest", {})
    props = request_schema.get("properties") or {}
    assert "selected_time_snapshot" not in props
    assert "selected_time" not in props
