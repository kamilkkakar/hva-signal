"""Hosted live is OFF by default. Clients cannot enable a live vendor.

Operator/server settings may flip a demo flag. GENERAL real vendor construction
stays refused via may_construct_real_vendor() / refuse_real_vendor() — always.
HOSTED_LIVE_REAL_VENDOR_ENABLED must never authorize FortyGuardHttpClient.

The sole construction path is bounded selected-time:
construct_bounded_selected_time_http_client() in type1_live, only when
BOUNDED_SELECTED_TIME_LIVE_ENABLED=true, only from POST /api/v1/live/selected-time.
No FortyGuard import here. No network.
"""

from __future__ import annotations

from typing import Any

from app.core.config import Settings


class HostedLiveDisabledError(RuntimeError):
    """Real hosted-live vendor path is closed in this program."""


def hosted_live_defaults_are_off() -> bool:
    """Settings *field defaults* — not env, not client — keep hosted live off."""
    fields = Settings.model_fields
    return (
        fields["hosted_live_enabled"].default is False
        and fields["hosted_live_real_vendor_enabled"].default is False
        and fields["demo_allowance_enabled"].default is False
        and int(fields["demo_allowance_max_total_units"].default) == 0
    )


def resolve_hosted_live(
    *,
    settings: Settings | None = None,
    client_headers: dict[str, str] | None = None,
    client_query: dict[str, Any] | str | None = None,
    client_body: dict[str, Any] | None = None,
) -> bool:
    """Server settings only. Header / query / body are accepted to prove ignore."""
    del client_headers, client_query, client_body
    current = settings if settings is not None else Settings.model_construct()
    return bool(getattr(current, "hosted_live_enabled", False))


def may_construct_real_vendor(settings: Settings | None = None) -> bool:
    """Always False. GENERAL vendor. Client and demo config cannot change this."""
    del settings
    return False


def refuse_real_vendor(settings: Settings | None = None) -> None:
    """Call at any GENERAL vendor-construction site. Always refuses."""
    del settings
    raise HostedLiveDisabledError(
        "this program will not construct a GENERAL live vendor; "
        "bounded selected-time uses construct_bounded_selected_time_http_client only"
    )


def acquisition_preference_cannot_enable_live(preference: str | None) -> bool:
    """allow_hosted_live_demo is user intent, never a vendor or spend gate."""
    del preference
    return True


def client_cannot_enable_hosted_live(settings: Settings | None = None) -> bool:
    """Invariant: any client enablement surface leaves hosted live unchanged."""
    closed = settings if settings is not None else Settings.model_construct()
    if resolve_hosted_live(settings=closed) is not False:
        return False
    attacks = (
        {"x-force-live": "1", "x-hosted-live-enabled": "true"},
        {"force_live": "true", "hosted_live_enabled": "1"},
        {
            "force_live": True,
            "hosted_live": True,
            "hosted_live_enabled": True,
            "allow_hosted_live_demo": True,
            "demo_allowance_enabled": True,
        },
    )
    headers, query, body = attacks
    return (
        resolve_hosted_live(
            settings=closed,
            client_headers=headers,
            client_query=query,
            client_body=body,
        )
        is False
        and may_construct_real_vendor(closed) is False
    )
