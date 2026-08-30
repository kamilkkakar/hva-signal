"""Fields a client must never set. Names only. No I/O. No spend grant.

LIVE-N public-safety contract. Hosted live stays operator/server-side.
"""

from __future__ import annotations

# Canonical names (snake_case). Header/query matching folds case and dashes.
CLIENT_NEVER_SET_FIELDS = frozenset(
    {
        "activity_id",
        "allowance",
        "allowance_cap",
        "allowance_remaining",
        "api_key",
        "apikey",
        "approval",
        "approval_ref",
        "approve",
        "approved",
        "authorize",
        "authorized",
        "authorized_max_units",
        "authorization_source",
        "budget",
        "bypass_cache",
        "bypass_limit",
        "cache_bust",
        "cache_key",
        "consumed_units",
        "demo",
        "demo_allowance_enabled",
        "demo_allowance_max_total_units",
        "demo_allowance_max_units_per_request",
        "demo_budget",
        "demo_test",
        "estimated_units",
        "force_live",
        "fortyguard_api_key",
        "grant",
        "hosted_live",
        "hosted_live_enabled",
        "hosted_live_real_vendor_enabled",
        "internal_key",
        "key",
        "live_demo",
        "max_total_acquisition_units",
        "max_units_per_request",
        "no_cache",
        "nocache",
        "operator",
        "operator_approval",
        "operator_id",
        "operator_override",
        "planned_acquisition_units",
        "requested_units",
        "reservation",
        "reservation_id",
        "reservation_state",
        "secret",
        "skip_approval",
        "spend",
        "spend_authorization",
        "spend_authorized",
        "spend_grant",
        "vendor_activity_id",
    }
)

# Headers that try to flip spend / live / recovery. Not general auth headers.
CLIENT_PRIVILEGE_HEADERS = frozenset(
    {
        "x-activity-id",
        "x-allowance",
        "x-allowance-cap",
        "x-allowance-remaining",
        "x-api-key",
        "x-budget",
        "x-bypass-cache",
        "x-bypass-limit",
        "x-cache-bust",
        "x-demo-allowance-enabled",
        "x-force-live",
        "x-fortyguard-api-key",
        "x-hosted-live",
        "x-hosted-live-enabled",
        "x-internal-key",
        "x-operator-approval",
        "x-reservation-id",
        "x-reservation-state",
        "x-vendor-activity-id",
    }
)

CLIENT_CACHE_BUST_FIELDS = frozenset(
    {
        "bypass_cache",
        "cache_bust",
        "cache_key",
        "no_cache",
        "nocache",
    }
)

HOSTED_LIVE_ENABLE_FIELDS = frozenset(
    {
        "demo_allowance_enabled",
        "force_live",
        "hosted_live",
        "hosted_live_enabled",
        "hosted_live_real_vendor_enabled",
        "live_demo",
    }
)
