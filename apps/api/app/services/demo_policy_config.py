"""Load demo allowance from server settings. Never accepts public request fields."""

from __future__ import annotations

from datetime import datetime

from app.core.config import Settings, get_settings
from app.domain.demo_allowance import DemoAllowancePolicy, disabled_demo_policy
from app.services.demo_allowance_ledger import InMemoryDemoAllowanceLedger
from app.services.demo_allowance_port import DemoAllowanceLedgerPort
from app.services.demo_allowance_store import SqliteDemoAllowanceStore


def _parse_optional_datetime(value: str | None) -> datetime | None:
    if value is None or not value.strip():
        return None
    return datetime.fromisoformat(value)


def demo_allowance_policy_from_settings(settings: Settings | None = None) -> DemoAllowancePolicy:
    """Fail closed. Settings are server-side; the client cannot set them."""
    current = settings or get_settings()
    enabled = bool(getattr(current, "demo_allowance_enabled", False))
    if not enabled:
        return disabled_demo_policy()
    areas = {
        item.strip()
        for item in str(getattr(current, "demo_allowance_allowed_areas", "")).split(",")
        if item.strip()
    }
    try:
        return DemoAllowancePolicy(
            enabled=True,
            valid_from=_parse_optional_datetime(
                getattr(current, "demo_allowance_valid_from", None)
            ),
            valid_until=_parse_optional_datetime(
                getattr(current, "demo_allowance_valid_until", None)
            ),
            max_total_acquisition_units=int(
                getattr(current, "demo_allowance_max_total_units", 0)
            ),
            max_units_per_request=int(
                getattr(current, "demo_allowance_max_units_per_request", 1)
            ),
            allowed_area_ids=frozenset(areas),
        )
    except (TypeError, ValueError):
        return disabled_demo_policy()


def demo_allowance_ledger_from_settings(
    settings: Settings | None = None,
    policy: DemoAllowancePolicy | None = None,
) -> DemoAllowanceLedgerPort:
    """Open J0 memory or J3 SQLite. A store path never enables hosted live."""
    current = settings or get_settings()
    resolved = policy or demo_allowance_policy_from_settings(current)
    path = str(getattr(current, "demo_allowance_store_path", "") or "").strip()
    ttl = int(getattr(current, "demo_allowance_reservation_ttl_seconds", 900))
    max_open = int(getattr(current, "demo_allowance_max_open_reservations", 8))
    if not path:
        return InMemoryDemoAllowanceLedger(resolved)
    return SqliteDemoAllowanceStore(
        path,
        resolved,
        reservation_ttl_seconds=ttl,
        max_open_reservations=max_open,
    )
