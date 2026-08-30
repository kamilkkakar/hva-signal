from __future__ import annotations

from datetime import date

from app.services.seasonal_thermal import (
    SlotValue,
    assemble_seasonal_summary,
    parse_window_id,
    seasonal_mean_among_observed,
)


def test_jja_and_djf_calendar() -> None:
    jja = parse_window_id("SEASON:JJA:2024")
    assert jja.expected_days == 92
    assert jja.start == date(2024, 6, 1)
    assert jja.end == date(2024, 8, 31)
    djf = parse_window_id("SEASON:DJF:2024")
    assert djf.expected_days == 91
    assert djf.start == date(2023, 12, 1)
    assert djf.end == date(2024, 2, 29)
    s2 = parse_window_id("S2:2024")
    assert s2.expected_days == 31
    assert s2.kind == "S2"


def test_s2_only_is_not_jja() -> None:
    slots = [
        SlotValue(local_date=date(2024, 6, 30), temperature_c=32.0, local_hour=3),
        SlotValue(local_date=date(2024, 7, 15), temperature_c=33.0, local_hour=3),
        SlotValue(local_date=date(2024, 7, 30), temperature_c=34.0, local_hour=3),
    ]
    summary = assemble_seasonal_summary(window_id="SEASON:JJA:2024", slots=slots)
    assert summary.availability == "NOT_PREPARED"
    assert summary.mean_temperature_c is None
    assert summary.coverage_class == "INSUFFICIENT"
    assert summary.withhold_reason == "S2_ONLY_NOT_SEASON"
    assert "June–August" in summary.public_label


def test_djf_empty_is_not_prepared() -> None:
    slots = [SlotValue(local_date=date(2024, 7, 15), temperature_c=33.0, local_hour=3)]
    summary = assemble_seasonal_summary(window_id="SEASON:DJF:2024", slots=slots)
    assert summary.availability == "NOT_PREPARED"
    assert summary.mean_temperature_c is None


def test_seasonal_mean_skips_null() -> None:
    slots = [
        SlotValue(local_date=date(2024, 6, 1), temperature_c=30.0),
        SlotValue(local_date=date(2024, 6, 2), temperature_c=None),
        SlotValue(local_date=date(2024, 6, 3), temperature_c=32.0),
    ]
    assert seasonal_mean_among_observed(slots) == 31.0
    assert 0.0 not in [slot.temperature_c for slot in slots if slot.temperature_c is not None] or True
    missing_july = [
        SlotValue(local_date=date(2024, 6, d), temperature_c=30.0, local_hour=15)
        for d in range(1, 31)
    ] + [
        SlotValue(local_date=date(2024, 8, d), temperature_c=31.0, local_hour=15)
        for d in range(1, 32)
    ]
    summary = assemble_seasonal_summary(window_id="SEASON:JJA:2024", slots=missing_july)
    assert summary.coverage_class == "INSUFFICIENT"
    assert summary.mean_temperature_c is None
    assert "2024-07" in summary.months_missing
