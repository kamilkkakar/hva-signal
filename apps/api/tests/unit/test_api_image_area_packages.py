"""API image must ship tracked area, context, and snapshot packages.

No ignored local trees. No workforce/. Layout tests use the Dockerfile
COPY destinations (/hackathon/data/...), not the git checkout alone.
"""

from __future__ import annotations

import shutil
from pathlib import Path

from fastapi.testclient import TestClient

from app.core.phoenix_v1_area_config import hackathon_root
from app.domain.observed_thermal_instants.assemble import (
    load_four_instant_differences,
    load_held_0300_means,
    load_tracked_snapshots,
)
from app.services.matched_nighttime_window import cached_nighttime_panel
from app.services.vulnerability_preparedness.cache import (
    load_context_bundle,
    reset_context_bundle_cache,
)

SEED = "04013107401"
ACTIVITY_1500 = "92086c4c-1550-4263-8ac8-9a6c9e030bc4"
ACTIVITY_2100 = "9865bd33-43a0-42b0-bc9b-74b27510002d"

REQUIRED_DATA_COPIES = (
    ("data/demo/phoenix", "/hackathon/data/demo/phoenix"),
    ("data/gate0", "/hackathon/data/gate0"),
    ("data/phoenix/reference", "/hackathon/data/phoenix/reference"),
    ("data/areas", "/hackathon/data/areas"),
    ("data/context/phoenix-demo", "/hackathon/data/context/phoenix-demo"),
    ("data/context/cross-city", "/hackathon/data/context/cross-city"),
    ("data/acquisitions/cross-city", "/hackathon/data/acquisitions/cross-city"),
    ("data/phoenix/snapshots", "/hackathon/data/phoenix/snapshots"),
)

GATE0_EVIDENCE_SCRIPTS = (
    "build_gate0_expected_tile_coverage.py",
    "gate0_between_aoi.py",
    "gate0_static_field.py",
    "gate0_static_field_audit.py",
)


def _dockerfile() -> str:
    return (hackathon_root() / "apps" / "api" / "Dockerfile").read_text(encoding="utf-8")


def test_dockerfile_copies_tracked_area_packages() -> None:
    dockerfile = _dockerfile()
    assert "COPY data/demo/phoenix" in dockerfile
    assert "COPY data/phoenix/reference" in dockerfile
    assert "COPY data/areas" in dockerfile
    assert "COPY data/context/cross-city" in dockerfile
    assert "COPY data/acquisitions/cross-city" in dockerfile
    assert "workforce" not in dockerfile


def test_dockerfile_copies_context_and_observed_instant_data() -> None:
    dockerfile = _dockerfile()
    for src, dest in REQUIRED_DATA_COPIES:
        assert f"COPY {src} {dest}" in dockerfile
    assert "workforce" not in dockerfile
    assert "p14_phase1" not in dockerfile


def test_dockerfile_copies_gate0_ledger_and_tracked_audit_scripts() -> None:
    dockerfile = _dockerfile()
    assert "COPY data/gate0 /hackathon/data/gate0" in dockerfile
    for filename in GATE0_EVIDENCE_SCRIPTS:
        assert (
            f"COPY scripts/{filename} /hackathon/scripts/{filename}" in dockerfile
        )
    assert "workforce" not in dockerfile


def test_tracked_runtime_files_exist_for_image_copy() -> None:
    root = hackathon_root()
    required = (
        root / "data" / "context" / "phoenix-demo" / "context_bundle.json",
        root / "data" / "context" / "phoenix-demo" / "SOURCE.json",
        root / "data" / "context" / "phoenix-demo" / "join_audit.json",
        root / "data" / "phoenix" / "snapshots" / "2024-07-08T15-00.snapshot.json",
        root / "data" / "phoenix" / "snapshots" / "2024-07-08T21-00.snapshot.json",
        root / "data" / "phoenix" / "reference" / "observations.jsonl",
        root / "data" / "phoenix" / "reference" / "four_instant_differences_2024-07-08.json",
    )
    missing = [path.as_posix() for path in required if not path.is_file()]
    assert missing == []


def _image_root_from_dockerfile(tmp_path: Path) -> Path:
    """Materialize only the data trees the Dockerfile COPY lines ship."""
    image_root = tmp_path / "hackathon"
    repo = hackathon_root()
    for line in _dockerfile().splitlines():
        stripped = line.strip()
        if not stripped.startswith("COPY data/"):
            continue
        parts = stripped.split()
        src = repo / parts[1]
        dest_posix = parts[2]
        assert dest_posix.startswith("/hackathon/")
        dest = image_root / dest_posix.removeprefix("/hackathon/")
        dest.parent.mkdir(parents=True, exist_ok=True)
        if src.is_dir():
            shutil.copytree(src, dest, dirs_exist_ok=True)
        else:
            shutil.copy2(src, dest)
    return image_root


def _point_loaders_at_image(monkeypatch, image_root: Path) -> None:
    def _root() -> Path:
        return image_root

    monkeypatch.setattr("app.core.phoenix_v1_area_config.hackathon_root", _root)
    monkeypatch.setattr("app.core.geography_paths.repository_root", _root)
    monkeypatch.setattr(
        "app.domain.observed_thermal_instants.assemble.hackathon_root", _root
    )
    monkeypatch.setattr(
        "app.services.vulnerability_preparedness.paths.repository_root", _root
    )
    monkeypatch.setattr(
        "app.domain.matched_nighttime_window.panel.hackathon_root", _root
    )
    load_tracked_snapshots.cache_clear()
    load_four_instant_differences.cache_clear()
    load_held_0300_means.cache_clear()
    cached_nighttime_panel.cache_clear()
    reset_context_bundle_cache()


def test_image_layout_has_context_and_snapshot_files(tmp_path: Path) -> None:
    image_root = _image_root_from_dockerfile(tmp_path)
    bundle = (
        image_root / "data" / "context" / "phoenix-demo" / "context_bundle.json"
    )
    snap_1500 = (
        image_root / "data" / "phoenix" / "snapshots" / "2024-07-08T15-00.snapshot.json"
    )
    snap_2100 = (
        image_root / "data" / "phoenix" / "snapshots" / "2024-07-08T21-00.snapshot.json"
    )
    assert bundle.is_file(), "API image layout is missing phoenix-demo context_bundle.json"
    assert snap_1500.is_file(), "API image layout is missing 15:00 snapshot"
    assert snap_2100.is_file(), "API image layout is missing 21:00 snapshot"
    assert not (image_root / "workforce").exists()


def test_gate0_ledger_resolves_from_api_image_layout(
    tmp_path: Path, monkeypatch
) -> None:
    from app.core.gate0_registry import load_phoenix_gate0_ledger

    repo = hackathon_root()
    image_root = _image_root_from_dockerfile(tmp_path)
    shutil.copytree(
        repo / "apps" / "api" / "app",
        image_root / "apps" / "api" / "app",
        dirs_exist_ok=True,
    )
    shutil.copytree(
        repo / "apps" / "api" / "tests" / "fixtures",
        image_root / "apps" / "api" / "tests" / "fixtures",
        dirs_exist_ok=True,
    )
    scripts = image_root / "scripts"
    scripts.mkdir(parents=True, exist_ok=True)
    for filename in GATE0_EVIDENCE_SCRIPTS:
        shutil.copy2(repo / "scripts" / filename, scripts / filename)

    _point_loaders_at_image(monkeypatch, image_root)
    monkeypatch.setattr("app.core.gate0_registry.hackathon_root", lambda: image_root)
    resolved = load_phoenix_gate0_ledger(root=image_root)
    assert resolved.ledger.overall_status.value == "OPEN"
    assert resolved.path == image_root / "data" / "gate0" / "phoenix-v1" / "ledger.json"
    assert not (image_root / "workforce").exists()


def test_context_loader_resolves_image_filesystem_layout(
    tmp_path: Path, monkeypatch
) -> None:
    image_root = _image_root_from_dockerfile(tmp_path)
    _point_loaders_at_image(monkeypatch, image_root)
    document = load_context_bundle(repo_root=image_root)
    assert document["area_id"] == "phoenix-demo"
    assert document["contract_version"] == "hva-signal-phoenix-context-v1"
    assert len((document.get("join_audit") or {}).get("zone_geoids") or []) == 25


def test_observed_instants_assemble_from_image_filesystem_layout(
    tmp_path: Path, monkeypatch
) -> None:
    image_root = _image_root_from_dockerfile(tmp_path)
    _point_loaders_at_image(monkeypatch, image_root)
    from app.domain.observed_thermal_instants.assemble import (
        assemble_observed_thermal_sequence,
    )

    seq = assemble_observed_thermal_sequence(SEED)
    by_id = {item.instant_id: item for item in seq.observations}
    assert by_id["15:00"].activity_id == ACTIVITY_1500
    assert by_id["21:00"].activity_id == ACTIVITY_2100
    assert "workforce" not in str(seq.as_dict())


def test_cross_city_metrics_read_image_filesystem_layout(
    tmp_path: Path, monkeypatch
) -> None:
    # Import the application before temporarily redirecting repository roots.
    # Otherwise a fresh test process can bind the temporary ``hackathon_root``
    # function into modules imported by app.main and leak it after monkeypatch
    # restores the source module.
    from app.main import app

    image_root = _image_root_from_dockerfile(tmp_path)
    _point_loaders_at_image(monkeypatch, image_root)
    monkeypatch.setattr(
        "app.api.routes.multicity._repo_root", lambda: image_root
    )
    monkeypatch.setattr(
        "app.domain.multicity.cross_city_acs._repo_root", lambda: image_root
    )
    monkeypatch.setattr(
        "app.domain.multicity.cross_city_canopy._repo_root", lambda: image_root
    )
    monkeypatch.setattr(
        "app.domain.multicity.cross_city_thermal._repo_root", lambda: image_root
    )
    from app.domain.multicity.cross_city_acs import load_city_acs
    from app.domain.multicity.cross_city_canopy import load_city_canopy
    from app.domain.multicity.cross_city_thermal import load_city_thermal_zones

    load_city_acs.cache_clear()
    load_city_canopy.cache_clear()
    load_city_thermal_zones.cache_clear()
    client = TestClient(app)
    response = client.get("/api/v1/cross-city/metrics")
    assert response.status_code == 200, response.text
    body = response.json()
    assert len(body["rows"]) == 100
    assert body["summary"]["included_count"] >= 99
    assert all(row["temperature_c"] is not None for row in body["rows"])
    assert all(row["tree_canopy_pct"] is not None for row in body["rows"])

    image_root = _image_root_from_dockerfile(tmp_path)
    _point_loaders_at_image(monkeypatch, image_root)
    from app.main import app

    client = TestClient(app)
    context = client.get("/api/v1/areas/phoenix-demo/context")
    assert context.status_code == 200, context.text
    assert context.json()["area_id"] == "phoenix-demo"

    night = client.get(
        "/api/v1/demo/matched-nighttime-window",
        params={"area_id": "phoenix-demo", "geoid": SEED},
    )
    assert night.status_code == 200, night.text
    assert night.json()["window_label"] == "MATCHED SUMMER NIGHTTIME WINDOW"

    instants = client.get(
        "/api/v1/demo/observed-thermal-instants",
        params={"area_id": "phoenix-demo", "geoid": SEED},
    )
    assert instants.status_code == 200, instants.text
    ids = [item["instant_id"] for item in instants.json()["observations"]]
    assert ids == ["03:00_D", "15:00", "21:00", "03:00_D+1"]
    by_id = {item["instant_id"]: item for item in instants.json()["observations"]}
    assert by_id["15:00"]["activity_id"] == ACTIVITY_1500
    assert by_id["21:00"]["activity_id"] == ACTIVITY_2100
