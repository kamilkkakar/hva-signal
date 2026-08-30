"""Canonical client-forbidden control-plane fields.

LIVE-J public safety. Names only — no vendor I/O, no secrets as values.
Client payloads, query strings, and headers must never set these.
"""

from __future__ import annotations

CATEGORY_ALLOWANCE_CAP = "allowance_cap"
CATEGORY_BUDGET = "budget"
CATEGORY_KEY = "key"
CATEGORY_FORCE_LIVE = "force_live"
CATEGORY_OPERATOR_APPROVAL = "operator_approval"
CATEGORY_RESERVATION_STATE = "reservation_state"

# (canonical snake_case, category)
_CANONICAL_FIELDS: tuple[tuple[str, str], ...] = (
    # Allowance cap — server/operator policy only
    ("allowance_cap", CATEGORY_ALLOWANCE_CAP),
    ("authorized_max_units", CATEGORY_ALLOWANCE_CAP),
    ("max_total_acquisition_units", CATEGORY_ALLOWANCE_CAP),
    ("max_total_units", CATEGORY_ALLOWANCE_CAP),
    ("max_units_per_request", CATEGORY_ALLOWANCE_CAP),
    ("demo_allowance_max_total_units", CATEGORY_ALLOWANCE_CAP),
    ("demo_allowance_max_units_per_request", CATEGORY_ALLOWANCE_CAP),
    ("requested_units", CATEGORY_ALLOWANCE_CAP),
    ("planned_acquisition_units", CATEGORY_ALLOWANCE_CAP),
    ("estimated_units", CATEGORY_ALLOWANCE_CAP),
    # Budget
    ("budget", CATEGORY_BUDGET),
    ("demo_budget", CATEGORY_BUDGET),
    ("spend_budget", CATEGORY_BUDGET),
    ("credit_budget", CATEGORY_BUDGET),
    ("allowance", CATEGORY_BUDGET),
    ("allowance_remaining", CATEGORY_BUDGET),
    # Key / secret material
    ("key", CATEGORY_KEY),
    ("api_key", CATEGORY_KEY),
    ("apikey", CATEGORY_KEY),
    ("internal_key", CATEGORY_KEY),
    ("fortyguard_api_key", CATEGORY_KEY),
    ("secret", CATEGORY_KEY),
    ("token", CATEGORY_KEY),
    ("access_token", CATEGORY_KEY),
    ("refresh_token", CATEGORY_KEY),
    ("bearer", CATEGORY_KEY),
    ("password", CATEGORY_KEY),
    ("private_key", CATEGORY_KEY),
    ("client_secret", CATEGORY_KEY),
    ("authorization", CATEGORY_KEY),
    # force_live / hosted live enablement
    ("force_live", CATEGORY_FORCE_LIVE),
    ("hosted_live", CATEGORY_FORCE_LIVE),
    ("hosted_live_enabled", CATEGORY_FORCE_LIVE),
    ("hosted_live_real_vendor_enabled", CATEGORY_FORCE_LIVE),
    ("enable_live", CATEGORY_FORCE_LIVE),
    ("enable_hosted_live", CATEGORY_FORCE_LIVE),
    ("allow_hosted_live", CATEGORY_FORCE_LIVE),
    ("allow_hosted_live_demo", CATEGORY_FORCE_LIVE),
    ("live_vendor", CATEGORY_FORCE_LIVE),
    ("live_demo", CATEGORY_FORCE_LIVE),
    ("demo_allowance_enabled", CATEGORY_FORCE_LIVE),
    ("demo", CATEGORY_FORCE_LIVE),
    ("demo_test", CATEGORY_FORCE_LIVE),
    # Operator approval — server-side only
    ("operator_approval", CATEGORY_OPERATOR_APPROVAL),
    ("operator_approved", CATEGORY_OPERATOR_APPROVAL),
    ("operator_override", CATEGORY_OPERATOR_APPROVAL),
    ("operator", CATEGORY_OPERATOR_APPROVAL),
    ("operator_id", CATEGORY_OPERATOR_APPROVAL),
    ("approval", CATEGORY_OPERATOR_APPROVAL),
    ("approved", CATEGORY_OPERATOR_APPROVAL),
    ("approve", CATEGORY_OPERATOR_APPROVAL),
    ("authorize", CATEGORY_OPERATOR_APPROVAL),
    ("authorized", CATEGORY_OPERATOR_APPROVAL),
    ("skip_approval", CATEGORY_OPERATOR_APPROVAL),
    ("spend_authorized", CATEGORY_OPERATOR_APPROVAL),
    ("spend_authorization", CATEGORY_OPERATOR_APPROVAL),
    ("authorization_source", CATEGORY_OPERATOR_APPROVAL),
    ("approval_ref", CATEGORY_OPERATOR_APPROVAL),
    ("awaiting_approval", CATEGORY_OPERATOR_APPROVAL),
    ("admin", CATEGORY_OPERATOR_APPROVAL),
    ("grant", CATEGORY_OPERATOR_APPROVAL),
    ("spend_grant", CATEGORY_OPERATOR_APPROVAL),
    ("bypass_limit", CATEGORY_OPERATOR_APPROVAL),
    # Reservation state — ledger/server only
    ("reservation", CATEGORY_RESERVATION_STATE),
    ("reservation_id", CATEGORY_RESERVATION_STATE),
    ("reservation_state", CATEGORY_RESERVATION_STATE),
    ("reservation_status", CATEGORY_RESERVATION_STATE),
    ("reserved", CATEGORY_RESERVATION_STATE),
    ("reserved_units", CATEGORY_RESERVATION_STATE),
    ("consume", CATEGORY_RESERVATION_STATE),
    ("consumed", CATEGORY_RESERVATION_STATE),
    ("consumed_units", CATEGORY_RESERVATION_STATE),
    ("ledger_state", CATEGORY_RESERVATION_STATE),
    ("activity_id", CATEGORY_RESERVATION_STATE),
    ("vendor_activity_id", CATEGORY_RESERVATION_STATE),
    ("force_consume", CATEGORY_RESERVATION_STATE),
    ("max_open_reservations", CATEGORY_RESERVATION_STATE),
    ("reservation_ttl_seconds", CATEGORY_RESERVATION_STATE),
    # Cache-bust / replay — client cannot force a vendor miss
    ("cache_bust", CATEGORY_FORCE_LIVE),
    ("bypass_cache", CATEGORY_FORCE_LIVE),
    ("cache_key", CATEGORY_FORCE_LIVE),
    ("no_cache", CATEGORY_FORCE_LIVE),
    ("nocache", CATEGORY_FORCE_LIVE),
    # Bare spend + F store path
    ("spend", CATEGORY_BUDGET),
    ("demo_allowance_store_path", CATEGORY_ALLOWANCE_CAP),
)

REQUIRED_CLIENT_NEVER_SET_CATEGORIES = frozenset(
    {
        CATEGORY_ALLOWANCE_CAP,
        CATEGORY_BUDGET,
        CATEGORY_KEY,
        CATEGORY_FORCE_LIVE,
        CATEGORY_OPERATOR_APPROVAL,
        CATEGORY_RESERVATION_STATE,
    }
)


def normalize_client_key(name: str) -> str:
    """Lowercase, hyphen/space → underscore, strip common header prefixes."""
    raw = str(name).strip().lower().replace("-", "_").replace(" ", "_")
    while "__" in raw:
        raw = raw.replace("__", "_")
    raw = raw.strip("_")
    if raw.startswith("http_"):
        raw = raw[5:]
    if raw.startswith("x_"):
        raw = raw[2:]
    return raw


def _alias_forms(canonical: str) -> set[str]:
    parts = [part for part in canonical.split("_") if part]
    kebab = "-".join(parts)
    camel = parts[0] + "".join(part.capitalize() for part in parts[1:])
    pascal = "".join(part.capitalize() for part in parts)
    compact = "".join(parts)
    forms = {
        canonical,
        kebab,
        camel,
        pascal,
        compact,
        canonical.upper(),
        kebab.upper(),
        f"x_{canonical}",
        f"x-{kebab}",
    }
    return forms


def _build_alias_map() -> dict[str, tuple[str, str]]:
    """normalized alias -> (canonical, category)."""
    mapping: dict[str, tuple[str, str]] = {}
    for canonical, category in _CANONICAL_FIELDS:
        for form in _alias_forms(canonical):
            mapping[normalize_client_key(form)] = (canonical, category)
            mapping[form.lower().replace("-", "_")] = (canonical, category)
        mapping[canonical] = (canonical, category)
    # Extra vendor-key spellings that skip underscore expansion
    for extra, canonical, category in (
        ("api-key", "api_key", CATEGORY_KEY),
        ("x-api-key", "api_key", CATEGORY_KEY),
        ("fortyguard-api-key", "fortyguard_api_key", CATEGORY_KEY),
        ("x-fortyguard-api-key", "fortyguard_api_key", CATEGORY_KEY),
        ("x-force-live", "force_live", CATEGORY_FORCE_LIVE),
        ("x-hosted-live", "hosted_live", CATEGORY_FORCE_LIVE),
        ("x-operator-approval", "operator_approval", CATEGORY_OPERATOR_APPROVAL),
        ("x-reservation-id", "reservation_id", CATEGORY_RESERVATION_STATE),
        ("x-allowance-cap", "allowance_cap", CATEGORY_ALLOWANCE_CAP),
        ("x-demo-budget", "demo_budget", CATEGORY_BUDGET),
        ("x-activity-id", "activity_id", CATEGORY_RESERVATION_STATE),
        ("x-vendor-activity-id", "vendor_activity_id", CATEGORY_RESERVATION_STATE),
        ("x-cache-bust", "cache_bust", CATEGORY_FORCE_LIVE),
        ("x-bypass-cache", "bypass_cache", CATEGORY_FORCE_LIVE),
        ("x-cache-key", "cache_key", CATEGORY_FORCE_LIVE),
        ("x-force-consume", "force_consume", CATEGORY_RESERVATION_STATE),
    ):
        mapping[normalize_client_key(extra)] = (canonical, category)
    return mapping


ALIAS_TO_FIELD: dict[str, tuple[str, str]] = _build_alias_map()

CLIENT_CONTROL_FIELD_NAMES: frozenset[str] = frozenset(
    canonical for canonical, _category in _CANONICAL_FIELDS
)

CLIENT_CONTROL_ALIASES: frozenset[str] = frozenset(ALIAS_TO_FIELD.keys())


def classify_client_control_field(name: str) -> tuple[str, str] | None:
    """Return (canonical, category) if this name is a forbidden client control field."""
    direct = ALIAS_TO_FIELD.get(normalize_client_key(name))
    if direct is not None:
        return direct
    raw = str(name).strip().lower().replace("-", "_").replace(" ", "_")
    return ALIAS_TO_FIELD.get(raw)
