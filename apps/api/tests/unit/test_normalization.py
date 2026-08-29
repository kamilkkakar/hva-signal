"""Hazard normalization: ABSOLUTE identity, HISTORICAL vs injected baseline, never AOI min-max."""

from __future__ import annotations

from pathlib import Path

import pytest

from app.core.area_config import AreaConfig
from app.domain.enums import ReferenceFrame

# Injected fixture series — not live Phoenix climatology and not probe numbers.
FIXTURE_BASELINE = [10.0, 20.0, 30.0, 40.0, 50.0]
PHOENIX_PROBE_STRINGS = ("0.003", "0.0003", "0.074")


def test_area_config_default_hazard_frame_remains_historical() -> None:
    assert (
        AreaConfig.model_fields["default_hazard_reference_frame"].default
        == ReferenceFrame.HISTORICAL
    )


def test_absolute_is_identity_on_tcm_celsius() -> None:
    from app.services.normalization import normalize_hazard

    feature = normalize_hazard(36.5, ReferenceFrame.ABSOLUTE)

    assert feature.raw_value == pytest.approx(36.5)
    assert feature.normalized_value == pytest.approx(36.5)
    assert feature.raw_value == feature.normalized_value
    assert feature.unit == "celsius"
    assert feature.reference_frame == ReferenceFrame.ABSOLUTE
    assert feature.normalized_value != 0


def test_historical_percentile_uses_injected_baseline() -> None:
    from app.services.normalization import normalize_hazard

    feature = normalize_hazard(
        30.0,
        ReferenceFrame.HISTORICAL,
        baseline_series=FIXTURE_BASELINE,
    )

    # Empirical percentile: share of baseline values <= 30 → 3/5 = 60.
    assert feature.raw_value == pytest.approx(30.0)
    assert feature.normalized_value == pytest.approx(60.0)
    assert feature.reference_frame == ReferenceFrame.HISTORICAL
    assert feature.unit == "percentile"
    assert "phoenix" not in feature.reference_definition.lower()


def test_historical_is_not_aoi_minmax() -> None:
    from app.services.normalization import normalize_hazard

    # AOI min-max of [29.9, 30.0, 30.1] would put 30.0 near 0.5.
    # Injected baseline [0, 50, 100]: 1 of 3 samples are <= 30 → ~33.3rd percentile.
    feature = normalize_hazard(
        30.0,
        ReferenceFrame.HISTORICAL,
        baseline_series=[0.0, 50.0, 100.0],
    )

    assert feature.normalized_value == pytest.approx(100.0 / 3.0)
    assert feature.normalized_value != pytest.approx(0.5)
    assert feature.normalized_value != pytest.approx((30.0 - 29.9) / (30.1 - 29.9))


def test_relative_frame_for_hazard_is_rejected() -> None:
    from app.services.normalization import (
        RelativeHazardNormalizationError,
        normalize_hazard,
    )

    with pytest.raises(RelativeHazardNormalizationError, match="RELATIVE"):
        normalize_hazard(
            30.0,
            ReferenceFrame.RELATIVE,
            baseline_series=FIXTURE_BASELINE,
        )


def test_missing_tcm_is_none_and_insufficient_never_zero() -> None:
    from app.services.normalization import normalize_hazard

    absolute = normalize_hazard(None, ReferenceFrame.ABSOLUTE)
    historical = normalize_hazard(
        None,
        ReferenceFrame.HISTORICAL,
        baseline_series=FIXTURE_BASELINE,
    )

    for feature in (absolute, historical):
        assert feature.raw_value is None
        assert feature.normalized_value is None
        assert feature.normalized_value != 0
        assert feature.raw_value != 0
        assert "insufficient_evidence" in feature.quality_flags


def test_empty_historical_baseline_is_insufficient_not_zero() -> None:
    from app.services.normalization import normalize_hazard

    feature = normalize_hazard(
        22.0,
        ReferenceFrame.HISTORICAL,
        baseline_series=[],
    )

    assert feature.raw_value == pytest.approx(22.0)
    assert feature.normalized_value is None
    assert feature.normalized_value != 0
    assert "insufficient_evidence" in feature.quality_flags


def test_historical_without_baseline_is_insufficient_not_invented_climatology() -> None:
    from app.services.normalization import normalize_hazard

    feature = normalize_hazard(22.0, ReferenceFrame.HISTORICAL)

    assert feature.normalized_value is None
    assert feature.normalized_value != 0
    assert "insufficient_evidence" in feature.quality_flags


def test_production_normalization_does_not_embed_phoenix_probe_numbers() -> None:
    services = Path(__file__).resolve().parents[2] / "app" / "services"
    for name in ("normalization.py", "normalization_registry.py"):
        src = services / name
        if not src.exists():
            continue
        text = src.read_text(encoding="utf-8")
        for needle in PHOENIX_PROBE_STRINGS:
            assert needle not in text
