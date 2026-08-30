"""Crash-matrix packages must not import FortyGuard or a real vendor."""

from __future__ import annotations

from pathlib import Path

from app.services.live_crash_matrix.fakes import FakeLiveVendor
from app.services.live_crash_matrix.production_gaps import assert_no_fortyguard_import

_API = Path(__file__).resolve().parents[2]
_PACKAGES = (
    _API / "app" / "domain" / "live_crash_matrix",
    _API / "app" / "services" / "live_crash_matrix",
)


def test_isolated_packages_do_not_import_fortyguard() -> None:
    offenders: list[str] = []
    for package in _PACKAGES:
        offenders.extend(assert_no_fortyguard_import(package))
    assert offenders == []


def test_fake_vendor_has_no_network_surface() -> None:
    vendor = FakeLiveVendor()
    assert vendor.kind == "fake"
    assert not hasattr(vendor, "base_url")
    assert not hasattr(vendor, "api_key")
    activity_id = vendor.submit("aa" * 32)
    assert activity_id.startswith("fake_")
    status = vendor.get_status(activity_id)
    assert status["status"] == "succeeded"
