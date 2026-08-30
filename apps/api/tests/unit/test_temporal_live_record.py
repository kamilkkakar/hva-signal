from __future__ import annotations

import json
from pathlib import Path

from app.services.temporal_assemble import assemble_daily_profile
from app.services.temporal_normalize import CACHED_ACTIVITY_ID
from tests.contract.temporal.conftest import TEMPORAL

LIVE = TEMPORAL / "live_record.json"


def test_live_calls_is_zero_or_one() -> None:
    record = json.loads(LIVE.read_text(encoding="utf-8"))
    assert record["schema"] == "TEMPORAL_LIVE_CALL_RECORD_V1"
    assert record["live_calls"] in {0, 1}
    assert record["live_calls"] == 0
    assert record["credit_delta"] == 0
    assert record["activity_id"] == CACHED_ACTIVITY_ID
    assert record["activity_id_role"] == "cached_reuse_not_a_new_submit"
    assert record["valid_zone_count"] == 25


def test_pytest_never_calls_fortyguard(monkeypatch) -> None:
    def _blocked(*_a, **_k):
        raise AssertionError("pytest must not call FortyGuard")

    monkeypatch.setattr("httpx.Client.request", _blocked)
    monkeypatch.setattr("httpx.AsyncClient.request", _blocked)
    record = json.loads(LIVE.read_text(encoding="utf-8"))
    assert record["live_calls"] == 0


def test_assemble_get_never_acquires() -> None:
    from datetime import date

    doc = assemble_daily_profile(
        area_id="phoenix-demo",
        zone_id="04013107401",
        local_date=date(2024, 7, 15),
        hours=None,
    )
    assert doc.availability == "NOT_PREPARED"
    assert doc.publication_status == "UNPUBLISHED"
    assert "spend" not in doc.payload
