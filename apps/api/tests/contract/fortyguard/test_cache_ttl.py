"""L2 operational/forecast TTL. Historical entries remain immutable."""

from datetime import date, datetime, timezone
from pathlib import Path

from app.integrations.fortyguard.cache import (
    OPERATIONAL_TTL_SECONDS,
    FortyGuardCache,
    operational_ttl_seconds,
    ttl_for_heatmap_payload,
)


def test_historical_put_without_ttl_does_not_expire(tmp_path: Path) -> None:
    clock = {"t": datetime(2024, 7, 15, 12, 0, tzinfo=timezone.utc)}
    cache = FortyGuardCache(tmp_path / "cache", now=lambda: clock["t"])
    cache.put("hist", {"result": {"ok": True}})
    clock["t"] = datetime(2026, 8, 27, 12, 0, tzinfo=timezone.utc)
    hit = cache.get("hist")
    assert hit is not None
    assert hit[0]["result"]["ok"] is True


def test_operational_ttl_expires(tmp_path: Path) -> None:
    clock = {"t": datetime(2026, 8, 27, 12, 0, tzinfo=timezone.utc)}
    cache = FortyGuardCache(tmp_path / "cache", now=lambda: clock["t"])
    cache.put("ops", {"result": {"ok": True}}, ttl_seconds=60)
    assert cache.get("ops") is not None
    clock["t"] = datetime(2026, 8, 27, 12, 2, tzinfo=timezone.utc)
    assert cache.get("ops") is None


def test_operational_ttl_policy_is_none_for_past_dates() -> None:
    assert operational_ttl_seconds("2024-07-15", today=date(2026, 8, 27)) is None
    assert (
        operational_ttl_seconds("2026-08-27", today=date(2026, 8, 27))
        == OPERATIONAL_TTL_SECONDS
    )
    assert (
        operational_ttl_seconds("2026-08-28", today=date(2026, 8, 27))
        == OPERATIONAL_TTL_SECONDS
    )


def test_heatmap_payload_uses_nested_start_date() -> None:
    historical = {"date_time": {"start_date": "2024-07-15", "filter_type": 1}}
    operational = {"date_time": {"start_date": "2026-08-27", "filter_type": 1}}
    today = date(2026, 8, 27)
    assert ttl_for_heatmap_payload(historical, today=today) is None
    assert ttl_for_heatmap_payload(operational, today=today) == OPERATIONAL_TTL_SECONDS
