"""Operator approval is server-side only.

A client payload, header, or query string can never grant approval.
Default is denied. No vendor I/O.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Literal

from app.core.config import Settings


@dataclass(frozen=True)
class OperatorApprovalDecision:
    approved: bool
    source: Literal["none", "server_settings"]


def resolve_operator_approval(
    *,
    settings: Settings | None = None,
    client_payload: dict[str, Any] | None = None,
    client_headers: dict[str, str] | None = None,
    client_query: dict[str, Any] | None = None,
) -> OperatorApprovalDecision:
    """Ignore every client surface. Only process settings may approve."""
    del client_payload, client_headers, client_query
    current = settings if settings is not None else Settings.model_construct()
    if bool(getattr(current, "operator_approval_enabled", False)):
        return OperatorApprovalDecision(True, "server_settings")
    return OperatorApprovalDecision(False, "none")


def client_approval_is_ignored(settings: Settings | None = None) -> bool:
    """Invariant: client true-flags do not change a closed operator decision."""
    closed = settings if settings is not None else Settings.model_construct()
    baseline = resolve_operator_approval(settings=closed)
    attacked = resolve_operator_approval(
        settings=closed,
        client_payload={
            "operator_approval": True,
            "approved": True,
            "skip_approval": True,
            "spend_authorized": True,
        },
        client_headers={"x-operator-approval": "true"},
        client_query={"approved": "1"},
    )
    return baseline == attacked and attacked.approved is False
