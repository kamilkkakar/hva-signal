from __future__ import annotations

from datetime import datetime, timezone

import pytest

from app.domain.temporal import local_to_utc
from app.services.aoi_timezone import AoiLocalTimeError
from app.services.daily_thermal_profile import ingest
from app.services.temporal_source import UtcImportError, import_valid_time, refuse_z_strip_import


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


def test_off_hour_not_rounded() -> None:
    with pytest.raises(AoiLocalTimeError):
        ingest(datetime(2024, 7, 15, 3, 15), tz="America/Phoenix")
