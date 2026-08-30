"""Client payloads cannot set allowance, spend, or reservation controls.

Server settings and the ledger own these fields. Hosted live stays off unless
an operator freezes demo_allowance_* on the process, never on the request.
"""

from __future__ import annotations

from typing import Any

CLIENT_NEVER_SET_ALLOWANCE_KEYS = frozenset(
    {
        "allowance",
        "allowance_cap",
        "allowance_remaining",
        "authorized_max_units",
        "budget",
        "demo_allowance_enabled",
        "demo_allowance_max_total_units",
        "demo_allowance_max_units_per_request",
        "demo_allowance_store_path",
        "demo_budget",
        "max_open_reservations",
        "max_total_acquisition_units",
        "max_units_per_request",
        "reservation_ttl_seconds",
        "key",
        "api_key",
        "apikey",
        "fortyguard_api_key",
        "internal_key",
        "secret",
        "force_live",
        "hosted_live_enabled",
        "hosted_live_real_vendor_enabled",
        "operator_approval",
        "operator_override",
        "operator",
        "approved",
        "approve",
        "approval",
        "skip_approval",
        "authorization_source",
        "spend_authorized",
        "reservation_state",
        "reservation_id",
        "reservation",
        "force_consume",
        "consume",
    }
)


def walk_payload_keys(value: Any) -> set[str]:
    found: set[str] = set()
    if isinstance(value, dict):
        for key, inner in value.items():
            found.add(str(key))
            found.update(walk_payload_keys(inner))
    elif isinstance(value, list):
        for item in value:
            found.update(walk_payload_keys(item))
    return found


def client_set_forbidden_allowance_keys(payload: dict[str, Any]) -> list[str]:
    """Return forbidden allowance/reservation keys present anywhere in a payload."""
    return sorted(CLIENT_NEVER_SET_ALLOWANCE_KEYS.intersection(walk_payload_keys(payload)))
