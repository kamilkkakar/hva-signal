"""Public OpenAPI must not grow a snapshot or prepare surface."""

from app.main import app


def test_public_openapi_has_no_signal_b_or_prepare_paths() -> None:
    schema = app.openapi()
    paths = schema.get("paths") or {}
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
    assert "SelectedTimeSnapshotZone" not in schemas
    request_schema = schemas.get("AnalysisRequest", {})
    props = request_schema.get("properties") or {}
    assert "selected_time_snapshot" not in props
    assert "selected_time" not in props
