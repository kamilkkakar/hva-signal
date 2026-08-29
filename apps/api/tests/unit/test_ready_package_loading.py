"""READY-package loading seam. Does not retune Decision 1B or Decision 8."""

from __future__ import annotations

from datetime import datetime
from pathlib import Path

import pytest

from app.core.phoenix_v1_area_config import (
    CANONICAL_REFERENCE_RELATIVE_PATH,
    hackathon_root,
    load_frozen_phoenix_v1_area_config,
)
from app.domain.phoenix_v1 import AREA_ID, FROZEN_AREA_CONFIG_SHA256
from app.domain.requests import AnalysisRequest
from app.services.phoenix_v1_reference import load_phoenix_v1_reference_panel


def _historical_request(day: str = "2022-07-01") -> AnalysisRequest:
    year, month, day_n = (int(part) for part in day.split("-"))
    return AnalysisRequest.model_validate(
        {
            "area_id": AREA_ID,
            "analysis_time": datetime(year, month, day_n, 3, 0),
            "analysis_mode": "retrospective",
            "horizon_hours": 0,
            "lookback_hours": 0,
            "granularity_m": 100,
            "data_mode": "replay",
        }
    )


def test_resolve_ready_package_exposes_verified_phoenix_artifacts() -> None:
    from app.core.area_registry import resolve_ready_area_package

    resolved = resolve_ready_area_package(AREA_ID)
    assert resolved.manifest.area_id == AREA_ID
    assert resolved.manifest.area_config_sha256 == FROZEN_AREA_CONFIG_SHA256
    assert resolved.config.area_id == AREA_ID
    assert resolved.reference_path == hackathon_root() / CANONICAL_REFERENCE_RELATIVE_PATH
    assert resolved.reference_path.is_file()
    frozen = load_frozen_phoenix_v1_area_config()
    assert resolved.config.version == frozen.version
    assert resolved.config.historical_reference_window.version == (
        frozen.historical_reference_window.version
    )


def test_phoenix_historical_job_uses_resolved_package_reference_path(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    from app.services import orchestrator

    recorded: dict[str, Path | None] = {}
    original = orchestrator.load_phoenix_v1_reference_panel

    def _spy(config, *, source_path=None):
        recorded["source_path"] = source_path
        return original(config, source_path=source_path)

    frozen_calls: list[str] = []
    inner = orchestrator.load_frozen_phoenix_v1_area_config

    def _guarded_frozen():
        frozen_calls.append("load")
        return inner()

    monkeypatch.setattr(orchestrator, "load_phoenix_v1_reference_panel", _spy)
    monkeypatch.setattr(orchestrator, "load_frozen_phoenix_v1_area_config", _guarded_frozen)

    result = orchestrator.run_replay_analysis(_historical_request("2022-07-01"))
    assert frozen_calls == ["load"]
    assert recorded["source_path"] == hackathon_root() / CANONICAL_REFERENCE_RELATIVE_PATH
    assert result.reference_quality == "FULL_REFERENCE"
    assert result.hazard_spread is not None
    assert result.hazard_spread.observed_spread is not None
    assert abs(result.hazard_spread.observed_spread - 0.0439665471923536) <= 1e-12


def test_phoenix_sufficient_job_unchanged_through_package_seam() -> None:
    from app.services.orchestrator import run_replay_analysis

    result = run_replay_analysis(_historical_request("2022-06-30"))
    assert result.thermal_differentiation_state == "SUFFICIENT"
    assert result.hazard_spread is not None
    assert result.hazard_spread.observed_spread is not None
    assert abs(result.hazard_spread.observed_spread - 0.13548387096774192) <= 1e-12


def test_inner_frozen_phoenix_loader_still_refuses_mutated_hash(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    from app.core import phoenix_v1_area_config as phoenix_cfg

    mutant = tmp_path / "area_config.json"
    mutant.write_text('{"area_id":"phoenix-demo"}\n', encoding="utf-8")
    monkeypatch.setattr(phoenix_cfg, "frozen_area_config_path", lambda: mutant)
    with pytest.raises(ValueError, match="SHA-256 mismatch"):
        phoenix_cfg.load_frozen_phoenix_v1_area_config()


def test_unknown_area_still_fails_closed() -> None:
    from app.core.area_registry import UnsupportedAreaError
    from app.services.orchestrator import run_replay_analysis

    with pytest.raises(UnsupportedAreaError, match="not-a-supported-area"):
        run_replay_analysis(
            AnalysisRequest.model_validate(
                {
                    "area_id": "not-a-supported-area",
                    "analysis_time": datetime(2022, 7, 1, 3, 0),
                    "analysis_mode": "retrospective",
                    "horizon_hours": 0,
                    "lookback_hours": 0,
                    "granularity_m": 100,
                    "data_mode": "replay",
                }
            )
        )


def test_load_phoenix_v1_reference_panel_still_uses_canonical_when_unspecified() -> None:
    config = load_frozen_phoenix_v1_area_config()
    panel = load_phoenix_v1_reference_panel(config)
    assert panel.quality == "FULL_REFERENCE"
    assert panel.row_count == 2325
