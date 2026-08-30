from __future__ import annotations

from pathlib import Path

from app.core.phoenix_v1_area_config import CANONICAL_REFERENCE_RELATIVE_PATH, hackathon_root
from app.domain.phoenix_v1 import THERMAL_AGGREGATION_VERSION, ZONE_GEOMETRY_VERSION
from app.domain.temporal import TemporalCoverageClass
from app.services.year_over_year import (
    PHOENIX_GEOMETRY_SHA256,
    YearSideSlots,
    YoYFrame,
    compare_s2_anchor_0300_from_reference_panel,
    compare_years,
)


def _frame(**overrides) -> YoYFrame:
    base = dict(
        window_id="S2:2023",
        sampling_design="ANCHOR_0300",
        zone_geometry_version=ZONE_GEOMETRY_VERSION,
        geometry_sha256=PHOENIX_GEOMETRY_SHA256,
        expected_zone_count=25,
        aggregation_spec_version=THERMAL_AGGREGATION_VERSION,
        source_mode="replay",
        temperature_quantity="tcm_zone_mean",
        timezone="America/Phoenix",
    )
    base.update(overrides)
    return YoYFrame(**base)


def test_geometry_mismatch_is_incomparable_no_delta() -> None:
    left_slots = YearSideSlots(
        year=2023,
        slots={("04013107401", "07-15"): 30.0},
        coverage_class=TemporalCoverageClass.FULL,
        coverage_ratio=1.0,
    )
    right_slots = YearSideSlots(
        year=2024,
        slots={("04013107401", "07-15"): 32.0},
        coverage_class=TemporalCoverageClass.FULL,
        coverage_ratio=1.0,
    )
    result = compare_years(
        left=_frame(),
        right=_frame(window_id="S2:2024", zone_geometry_version="OTHER-GEOMETRY"),
        left_slots=left_slots,
        right_slots=right_slots,
    )
    assert result.comparability == "INCOMPARABLE"
    assert result.mean_difference_c is None
    assert "G-GEO-1" in result.fail_closed_reasons


def test_yoy_82_vs_99_no_headline_delta() -> None:
    left_slots = YearSideSlots(
        year=2023,
        slots={("z", f"07-{d:02d}"): 30.0 for d in range(1, 26)},
        coverage_class=TemporalCoverageClass.ADEQUATE,
        coverage_ratio=0.82,
    )
    right_slots = YearSideSlots(
        year=2024,
        slots={("z", f"07-{d:02d}"): 31.0 for d in range(1, 32)},
        coverage_class=TemporalCoverageClass.FULL,
        coverage_ratio=0.99,
    )
    result = compare_years(
        left=_frame(),
        right=_frame(window_id="S2:2024"),
        left_slots=left_slots,
        right_slots=right_slots,
    )
    assert result.comparability == "COMPARABLE"
    assert result.pair_coverage_class == "PARTIAL"
    assert result.mean_difference_c is None


def test_s2_panel_candidate_delta_is_not_summer() -> None:
    path = hackathon_root() / CANONICAL_REFERENCE_RELATIVE_PATH
    result = compare_s2_anchor_0300_from_reference_panel(path, year_earlier=2023, year_later=2024)
    assert result.comparability == "COMPARABLE"
    assert result.mean_difference_c is not None
    assert "summer" not in result.label.lower()
    assert "S2" in result.label
    assert "3 a.m." in result.label
    assert result.public_sentence and "Not summer" in result.public_sentence


def test_2025_fails_closed() -> None:
    path = Path("unused")
    result = compare_s2_anchor_0300_from_reference_panel(path, year_earlier=2024, year_later=2025)
    assert result.comparability == "INCOMPARABLE"
    assert result.mean_difference_c is None
    assert "YY-2025" in result.fail_closed_reasons


def test_s2_versus_jja_is_incomparable() -> None:
    result = compare_years(
        left=_frame(),
        right=_frame(window_id="SEASON:JJA:2024"),
        left_slots=YearSideSlots(2023, {("z", "07-15"): 30.0}, TemporalCoverageClass.FULL, 1.0),
        right_slots=YearSideSlots(2024, {("z", "07-15"): 31.0}, TemporalCoverageClass.FULL, 1.0),
    )
    assert result.comparability == "INCOMPARABLE"
    assert result.mean_difference_c is None
