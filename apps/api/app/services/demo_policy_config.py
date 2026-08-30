"""Load demo allowance from server settings. Never accepts public request fields."""

from __future__ import annotations

from datetime import datetime

from app.core.config import Settings, get_settings
from app.domain.demo_allowance import DemoAllowancePolicy, disabled_demo_policy


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
