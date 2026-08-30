"""Provider-neutral abuse guards. No auth provider. No vendor I/O."""

from __future__ import annotations

from typing import Any

from app.domain.client_privilege import CLIENT_NEVER_SET_FIELDS
from app.domain.enums import DataMode
from app.services.spend_gate import SpendGrant


_CLIENT_AUTHORIZATION_KEYS = frozenset(
    {
        "approved",
        "authorize",
        "authorized",
        "skip_approval",
        "admin",
        "operator_override",
        "spend_authorized",
        "demo",
        "demo_test",
        "live_demo",
        "force_live",
        "allowance",
        "demo_budget",
        "internal_key",
        "bypass_limit",
        "allowance_remaining",
        "authorized_max_units",
    }
) | CLIENT_NEVER_SET_FIELDS


def client_flags_cannot_authorize(payload: dict[str, Any]) -> list[str]:
    """A request body must never carry its own spend approval."""
    return sorted(key for key in payload if key in _CLIENT_AUTHORIZATION_KEYS)


def data_mode_cannot_authorize(data_mode: DataMode) -> bool:
    """Every data_mode, including LIVE, is a fetch mode rather than a spend grant."""
    del data_mode
    return True


def grant_identity(
    grant: SpendGrant,
) -> tuple[str, str, str]:
    return (grant.signal_kind.value, grant.request_fingerprint, grant.geometry_sha256)


def grant_may_cover_request(
    grant: SpendGrant,
    *,
    signal_kind: str,
    request_fingerprint: str,
    geometry_sha256: str,
) -> bool:
    return grant_identity(grant) == (signal_kind, request_fingerprint, geometry_sha256)
