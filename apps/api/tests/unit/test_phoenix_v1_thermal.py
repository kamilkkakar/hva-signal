"""State separation for thermal observation, q_A, Decision 8, and reference quality."""

from __future__ import annotations

from datetime import date, timedelta

from app.domain.enums import (
    ReferenceEvidenceQuality,
    SystemLimitationCode,
    ThermalDifferentiationState,
)
from app.domain.phoenix_v1 import OBS_PER_YEAR, REFERENCE_YEARS, decision8_policy_fixture
from app.services.phoenix_v1_thermal import (
    evaluate_phoenix_v1_timestamp,
    observations_from_jsonl_rows,
)
from app.services.temporal_anomaly import ReferenceObservation


def _dates(year: int) -> list[str]:
    start = date(year, 6, 30)
    return [(start + timedelta(days=i)).isoformat() for i in range(OBS_PER_YEAR)]


def _panel(values_for: dict[str, float]) -> list[ReferenceObservation]:
    rows: list[ReferenceObservation] = []
    for geoid, base in values_for.items():
        for year in REFERENCE_YEARS:
            for day in _dates(year):
                rows.append(
                    ReferenceObservation(
                        date=day,
                        year=year,
                        geoid=geoid,
                        mean_tcm_c=base,
                    )
                )
    return rows


def _geoids() -> list[str]:
    return [f"0401310{i:04d}" for i in range(25)]


def _panel_with_target_q_a_spread(target_date: str = "2024-07-15") -> list[ReferenceObservation]:
    geoids = _geoids()
    rows: list[ReferenceObservation] = []
    for i, geoid in enumerate(geoids):
        for year in REFERENCE_YEARS:
            for day in _dates(year):
                if day == target_date:
                    if i < 3:
                        tcm = 10.0
                    elif i >= 22:
                        tcm = 40.0
                    else:
                        tcm = 25.0
                else:
                    tcm = 25.0
                rows.append(
                    ReferenceObservation(
                        date=day,
                        year=year,
                        geoid=geoid,
                        mean_tcm_c=tcm,
                    )
                )
    return rows


def test_case_a_full_reference_valid_q_a_sufficient_ordering() -> None:
    panel = _panel_with_target_q_a_spread()
    result = evaluate_phoenix_v1_timestamp("2024-07-15", panel)
    assert result.reference_quality == ReferenceEvidenceQuality.FULL_REFERENCE.value
    assert all(zone.thermal_state_valid and zone.q_A is not None for zone in result.zones)
    assert result.differentiation_state == ThermalDifferentiationState.SUFFICIENT.value
    assert result.thermal_ordering_permitted is True
    assert result.observed_spread is not None and result.observed_spread >= 0.10
    assert SystemLimitationCode.INSUFFICIENT_REFERENCE.value not in result.system_limitations
    assert (
        SystemLimitationCode.THERMAL_SPATIAL_DIFFERENTIATION_INSUFFICIENT.value
        not in result.system_limitations
    )
    assert result.provenance.policy_version == decision8_policy_fixture().version
    assert result.provenance.observed_spread == result.observed_spread


def test_case_b_full_reference_valid_q_a_insufficient_differentiation_keeps_thermal_state() -> None:
    geoids = _geoids()
    panel = _panel({geoid: 30.0 for geoid in geoids})
    result = evaluate_phoenix_v1_timestamp("2024-07-15", panel)
    assert result.reference_quality == ReferenceEvidenceQuality.FULL_REFERENCE.value
    assert all(zone.thermal_state_valid and zone.q_A is not None for zone in result.zones)
    assert result.differentiation_state == ThermalDifferentiationState.INSUFFICIENT.value
    assert result.thermal_ordering_permitted is False
    assert result.observed_spread is not None and result.observed_spread < 0.10
    assert (
        SystemLimitationCode.THERMAL_SPATIAL_DIFFERENTIATION_INSUFFICIENT.value
        in result.system_limitations
    )
    assert SystemLimitationCode.INSUFFICIENT_REFERENCE.value not in result.system_limitations
    assert result.provenance.suppression_reason
    assert result.provenance.input_quantity == "q_A"


def test_case_c_insufficient_reference_is_not_decision8_insufficient() -> None:
    geoids = _geoids()[:24]
    panel = _panel({geoid: 30.0 for geoid in geoids})
    result = evaluate_phoenix_v1_timestamp("2024-07-15", panel)
    assert result.reference_quality == ReferenceEvidenceQuality.INSUFFICIENT_REFERENCE.value
    assert result.differentiation_state == ThermalDifferentiationState.NOT_EVALUATED.value
    assert result.thermal_ordering_permitted is False
    assert result.observed_spread is None
    assert SystemLimitationCode.INSUFFICIENT_REFERENCE.value in result.system_limitations
    assert (
        SystemLimitationCode.THERMAL_SPATIAL_DIFFERENTIATION_INSUFFICIENT.value
        not in result.system_limitations
    )


def test_observations_from_jsonl_rows_pads_geoid() -> None:
    rows = observations_from_jsonl_rows(
        [{"date": "2022-06-30", "year": 2022, "geoid": "4013100000", "mean_tcm_c": 31.2}]
    )
    assert rows[0].geoid == "04013100000"


def test_out_of_panel_target_observations_keep_full_reference_and_compute_q_a() -> None:
    geoids = _geoids()
    panel = _panel({geoid: 25.0 for geoid in geoids})
    target = [
        ReferenceObservation(
            date="2025-07-15",
            year=2025,
            geoid=geoid,
            mean_tcm_c=10.0 if i < 3 else 40.0 if i >= 22 else 25.0,
        )
        for i, geoid in enumerate(geoids)
    ]
    missing = evaluate_phoenix_v1_timestamp("2025-07-15", panel)
    assert missing.differentiation_state == ThermalDifferentiationState.NOT_EVALUATED.value
    assert missing.reference_quality == ReferenceEvidenceQuality.INSUFFICIENT_REFERENCE.value

    result = evaluate_phoenix_v1_timestamp(
        "2025-07-15",
        panel,
        target_observations=target,
    )
    assert result.reference_quality == ReferenceEvidenceQuality.FULL_REFERENCE.value
    assert len(result.zones) == 25
    assert all(zone.thermal_state_valid and zone.q_A is not None for zone in result.zones)
    assert result.differentiation_state == ThermalDifferentiationState.SUFFICIENT.value
    assert result.thermal_ordering_permitted is True
    assert result.observed_spread is not None and result.observed_spread >= 0.10
    assert SystemLimitationCode.INSUFFICIENT_REFERENCE.value not in result.system_limitations
    assert "2025" not in {row.date[:4] for row in panel}


def test_incomplete_target_observations_are_not_evaluated() -> None:
    geoids = _geoids()
    panel = _panel({geoid: 25.0 for geoid in geoids})
    target = [
        ReferenceObservation(date="2025-07-15", year=2025, geoid=geoids[0], mean_tcm_c=30.0)
    ]
    result = evaluate_phoenix_v1_timestamp(
        "2025-07-15",
        panel,
        target_observations=target,
    )
    assert result.reference_quality == ReferenceEvidenceQuality.FULL_REFERENCE.value
    assert result.differentiation_state == ThermalDifferentiationState.NOT_EVALUATED.value
    assert result.observed_spread is None
    assert result.thermal_ordering_permitted is False
    assert (
        SystemLimitationCode.THERMAL_SPATIAL_DIFFERENTIATION_INSUFFICIENT.value
        not in result.system_limitations
    )
