"""Structural secret handling. The FortyGuard key never enters public DTOs."""

from __future__ import annotations

from typing import Any

_SECRET_KEYS = frozenset(
    {
        "fortyguard_api_key",
        "api_key",
        "apikey",
        "internal_key",
        "secret",
        "password",
        "authorization",
        "demo_budget",
        "allowance_remaining",
        "key",
        "token",
        "access_token",
        "refresh_token",
        "bearer",
        "private_key",
        "client_secret",
    }
)


def public_payload_leaks_secrets(payload: dict[str, Any]) -> list[str]:
    return sorted(key for key in _walk_keys(payload) if key in _SECRET_KEYS)


def _walk_keys(value: Any) -> set[str]:
    found: set[str] = set()
    if isinstance(value, dict):
        for key, inner in value.items():
            found.add(str(key))
            found.update(_walk_keys(inner))
    elif isinstance(value, list):
        for item in value:
            found.update(_walk_keys(item))
    return found
