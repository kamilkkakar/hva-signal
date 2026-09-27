from __future__ import annotations

from datetime import datetime, timezone

import pytest

from app.domain.temporal import (
    CLOCK_STAMP_CONTRACT_VERSION,
    clock_stamp_from_utc,
    local_to_utc,
)
from app.services.aoi_timezone import AoiLocalTimeError, TimezoneFailureCode
from app.services.daily_thermal_profile import ingest
from app.services.temporal_source import (
    UtcImportError,
    import_clock_stamp,
    import_valid_time,
    refuse_z_strip_import,
)


def test_phoenix_0300_is_1000_utc() -> None:
    local = datetime(2024, 7, 15, 3, 0, 0)
    utc = local_to_utc(local, "America/Phoenix")
    assert utc == datetime(2024, 7, 15, 10, 0, tzinfo=timezone.utc)
    assert local.tzinfo is None


def test_utc_z_converts_not_strips() -> None:
    local, utc = import_valid_time("2024-07-15T10:00:00Z", iana="America/Phoenix")
    assert local == datetime(2024, 7, 15, 3, 0, 0)
    assert utc == datetime(2024, 7, 15, 10, 0, tzinfo=timezone.utc)
    converted = refuse_z_strip_import("2024-07-15T10:00:00Z", iana="America/Phoenix")
    assert converted[0].hour == 3


def test_naive_utc_clock_is_not_a_legal_import() -> None:
    with pytest.raises(UtcImportError):
        refuse_z_strip_import("2024-07-15T10:00:00", iana="America/Phoenix")
    with pytest.raises(UtcImportError):
        import_valid_time(
            datetime(2024, 7, 15, 10, 0, 0),
            iana="America/Phoenix",
            assume_naive_is="forbidden_utc_naive",
        )


def test_phoenix_civil_day_is_24_hours() -> None:
    hours = [datetime(2024, 7, 15, h, 0, 0) for h in range(24)]
    for ts in hours:
        ingest(ts, tz="America/Phoenix")
    assert len(hours) == 24


def test_anchorage_naive_gap_and_overlap_fail_closed() -> None:
    with pytest.raises(AoiLocalTimeError) as gap:
        local_to_utc(datetime(2026, 3, 8, 2, 0), "America/Anchorage")
    assert gap.value.code is TimezoneFailureCode.NONEXISTENT_LOCAL_TIME

    with pytest.raises(AoiLocalTimeError) as overlap:
        local_to_utc(datetime(2026, 11, 1, 1, 0), "America/Anchorage")
    assert overlap.value.code is TimezoneFailureCode.AMBIGUOUS_LOCAL_TIME


def test_anchorage_repeated_hour_stamps_both_utc_instants() -> None:
    first = import_clock_stamp("2026-11-01T09:00:00Z", iana="America/Anchorage")
    second = import_clock_stamp("2026-11-01T10:00:00Z", iana="America/Anchorage")

    assert first.contract_version == CLOCK_STAMP_CONTRACT_VERSION
    assert first.valid_time_local == second.valid_time_local == datetime(2026, 11, 1, 1)
    assert (first.utc_offset_minutes, first.fold, first.local_time_status) == (
        -480,
        0,
        "ambiguous",
    )
    assert (second.utc_offset_minutes, second.fold, second.local_time_status) == (
        -540,
        1,
        "ambiguous",
    )
    assert first.valid_time_utc != second.valid_time_utc


def test_clock_stamp_rejects_inconsistent_offset_or_fold() -> None:
    stamp = clock_stamp_from_utc(
        datetime(2026, 11, 1, 10, tzinfo=timezone.utc), "America/Anchorage"
    )
    with pytest.raises(ValueError, match="utc_offset_minutes"):
        stamp.model_copy(update={"utc_offset_minutes": -480}).model_validate(
            stamp.model_copy(update={"utc_offset_minutes": -480}).model_dump()
        )
    with pytest.raises(ValueError, match="fold"):
        stamp.model_copy(update={"fold": 0}).model_validate(
            stamp.model_copy(update={"fold": 0}).model_dump()
        )


def test_off_hour_not_rounded() -> None:
    with pytest.raises(AoiLocalTimeError):
        ingest(datetime(2024, 7, 15, 3, 15), tz="America/Phoenix")
