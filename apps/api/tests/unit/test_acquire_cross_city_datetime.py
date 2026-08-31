"""Zero-spend tests for temporal acquire datetime plumbing.

Does not call FortyGuard. Imports operator helpers from scripts/acquire_cross_city_type1.py.
"""

from __future__ import annotations

import importlib.util
import sys
from datetime import datetime
from pathlib import Path

import pytest

_TEST_FILE = Path(__file__).resolve()
SCRIPT_PATH = _TEST_FILE.parents[4] / "scripts" / "acquire_cross_city_type1.py"
API_ROOT = _TEST_FILE.parents[2]
if str(API_ROOT) not in sys.path:
    sys.path.insert(0, str(API_ROOT))


def _load_acquire():
    spec = importlib.util.spec_from_file_location(
        "acquire_cross_city_type1", SCRIPT_PATH
    )
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


@pytest.fixture(scope="module")
def acq():
    return _load_acquire()


def test_default_remains_published_1500(acq):
    assert acq.DEFAULT_TARGET_LOCAL == datetime(2024, 7, 8, 15, 0, 0)
    assert acq.TARGET_LOCAL == acq.DEFAULT_TARGET_LOCAL
    assert acq.parse_approved_local_datetime("2024-07-08T15:00:00") == datetime(
        2024, 7, 8, 15, 0, 0
    )
    assert acq.acquisition_out_root("los_angeles", acq.DEFAULT_TARGET_LOCAL) == (
        acq.ROOT / "data" / "acquisitions" / "cross-city" / "los_angeles"
    )


def test_arbitrary_approved_datetime_accepted(acq):
    for stamp in (
        "2024-07-08T03:00:00",
        "2024-07-08T21:00:00",
        "2024-07-09T03:00:00",
    ):
        parsed = acq.parse_approved_local_datetime(stamp)
        assert parsed == datetime.fromisoformat(stamp)
        out = acq.acquisition_out_root("las_vegas", parsed)
        assert out.name == parsed.strftime("%Y%m%dT%H%M%S")
        assert out.parent.name == "matched"


def test_unapproved_datetime_rejected(acq):
    with pytest.raises(SystemExit, match="approved matrix"):
        acq.parse_approved_local_datetime("2024-07-08T12:00:00")


def test_timezone_utc_correctness(acq):
    # All four cities are UTC−7 in July (PDT / America/Phoenix).
    cases = [
        ("America/Los_Angeles", datetime(2024, 7, 8, 3, 0, 0), "2024-07-08T10:00:00Z"),
        ("America/Los_Angeles", datetime(2024, 7, 8, 21, 0, 0), "2024-07-09T04:00:00Z"),
        ("America/Los_Angeles", datetime(2024, 7, 9, 3, 0, 0), "2024-07-09T10:00:00Z"),
        ("America/Phoenix", datetime(2024, 7, 8, 3, 0, 0), "2024-07-08T10:00:00Z"),
        ("America/Phoenix", datetime(2024, 7, 8, 15, 0, 0), "2024-07-08T22:00:00Z"),
        ("America/Phoenix", datetime(2024, 7, 8, 21, 0, 0), "2024-07-09T04:00:00Z"),
    ]
    for tz_name, local, expected in cases:
        assert acq.provider_utc_iso(tz_name, local) == expected


def test_fingerprint_correctness_for_approved_clocks(acq):
    from app.domain.multicity.type1_live import dry_run_type1_preflight

    # Matrix row 1 (LV 03:00) + published 15:00 regression for Tucson.
    lv_03 = dry_run_type1_preflight(
        {
            "city": "Las Vegas",
            "target_local": datetime(2024, 7, 8, 3, 0, 0),
            "key_alias": "VALIDATION_B",
        }
    )
    assert (
        lv_03["request_fingerprint"]
        == "88b650171311db6759d10430adf5c966a44542e6db4e396d7a007d7b5ba1c57c"
    )
    assert (
        lv_03["cache_fingerprint"]
        == "1322c7dc6c2a751c1b3849eda4ea83061d799721910d857ab314e9c04bd4b04b"
    )
    assert lv_03["local_time"] == "2024-07-08T03:00:00"
    assert lv_03["provider_resolved_time"]["timezone"] == "America/Los_Angeles"

    tuc_15 = dry_run_type1_preflight(
        {
            "city": "Tucson",
            "target_local": acq.DEFAULT_TARGET_LOCAL,
            "key_alias": "VALIDATION_B",
        }
    )
    # Published CROSS_CITY_OBSERVATION_V1 fingerprints must still match V2 package.
    v2 = acq._city_package("tucson")
    assert tuc_15["request_fingerprint"] == v2["request_fingerprint"]
    assert tuc_15["cache_fingerprint"] == v2["cache_fingerprint"]
    assert tuc_15["local_time"] == "2024-07-08T15:00:00"


def test_preflight_gate_1500_regression(acq, monkeypatch):
    # Avoid requiring operator key env for gate-only path.
    gate = acq._preflight_gate("Los Angeles", "VALIDATION_B", target_local=acq.DEFAULT_TARGET_LOCAL)
    assert gate["target_local"] == acq.DEFAULT_TARGET_LOCAL
    assert gate["provider_utc"] == "2024-07-08T22:00:00Z"
    assert gate["checks"]["local_time"] is True
    assert gate["checks"]["request_fp"] is True
    assert gate["checks"]["cache_fp"] is True
    assert gate["preflight"]["resolution"] == "100m"
    assert gate["preflight"]["partition_count"] == 1


def test_preflight_gate_approved_matched_instant(acq):
    local = datetime(2024, 7, 8, 3, 0, 0)
    gate = acq._preflight_gate("Las Vegas", "VALIDATION_B", target_local=local)
    assert gate["target_local"] == local
    assert gate["provider_utc"] == "2024-07-08T10:00:00Z"
    assert gate["checks"]["local_time"] is True
    assert gate["checks"]["timezone"] is True
    assert (
        gate["preflight"]["request_fingerprint"]
        == "88b650171311db6759d10430adf5c966a44542e6db4e396d7a007d7b5ba1c57c"
    )


def test_peek_vendor_cache_hit_no_http(acq, tmp_path):
    """Operator acquire helper: seeded vendor cache must short-circuit before submit."""
    from app.integrations.fortyguard.cache import FortyGuardCache
    from app.integrations.fortyguard.transport_models import (
        DataMode,
        HeatmapFetchRequest,
        HeatmapTemporalMode,
    )

    from app.domain.multicity.city_catalog import resolve_city_aoi

    cfg = resolve_city_aoi("Los Angeles")
    request = HeatmapFetchRequest(
        polygon_aoi=cfg.polygon_aoi,
        start_date="2024-07-08",
        start_time="03:00",
        temporal_mode=HeatmapTemporalMode.SINGLE_HOUR,
        granularity=100,
        analytic_type="tcm",
        data_mode=DataMode.LIVE,
    )
    fingerprint = acq.vendor_cache_fingerprint_for_request(request)
    cache = FortyGuardCache(tmp_path / "vendor_cache")
    cache.put(
        fingerprint,
        {
            "activity_id": "seeded-activity-no-new-submit",
            "result": {"map_data": {"type": "FeatureCollection", "features": []}},
        },
    )
    peeked = acq.peek_vendor_cache(tmp_path / "vendor_cache", request)
    assert peeked is not None
    fp, body = peeked
    assert fp == fingerprint
    assert body["activity_id"] == "seeded-activity-no-new-submit"
    assert acq.peek_vendor_cache(tmp_path / "empty", request) is None


def test_ambiguous_failed_prior_does_not_blind_retry(acq, monkeypatch):
    """Timeout/disconnect provenance must refuse silent re-submit."""
    import json
    import shutil

    out_root = (
        acq.ROOT
        / "data"
        / "acquisitions"
        / "cross-city"
        / "_tmp_ambiguous_gate_test"
        / "matched"
        / "20240708T030000"
    )
    if out_root.exists():
        shutil.rmtree(out_root.parent.parent)
    out_root.mkdir(parents=True)
    (out_root / "raw").mkdir()
    (out_root / "normalized").mkdir()
    (out_root / "vendor_cache").mkdir()
    (out_root / "provenance.json").write_text(
        json.dumps(
            {
                "status": "failed",
                "vendor_attempted": True,
                "error_type": "TimeoutError",
                "activity_id": None,
            }
        ),
        encoding="utf-8",
    )
    monkeypatch.setattr(acq, "acquisition_out_root", lambda *_a, **_k: out_root)
    monkeypatch.setattr(
        acq,
        "_load_key_alias",
        lambda: ("VALIDATION_B", "test-key-not-real", "https://example.invalid"),
    )
    try:
        with pytest.raises(SystemExit, match="ambiguous prior execution"):
            acq.acquire_city("Los Angeles", target_local="2024-07-08T03:00:00")
    finally:
        shutil.rmtree(out_root.parent.parent, ignore_errors=True)
