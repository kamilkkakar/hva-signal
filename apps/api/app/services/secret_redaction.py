"""Redact secrets for logs and public responses.

Never log or return key material. Field names may appear; values must not.
No FortyGuard import. No vendor I/O.
"""

from __future__ import annotations

import logging
from typing import Any, Iterable

from app.domain.public_safety_fields import (
    CATEGORY_KEY,
    classify_client_control_field,
)

REDACTED = "[REDACTED]"

_SECRET_NAME_EXTRAS = frozenset(
    {
        "fortyguard_api_key",
        "api_key",
        "apikey",
        "api-key",
        "internal_key",
        "client_secret",
        "private_key",
        "password",
        "secret",
        "token",
        "access_token",
        "refresh_token",
        "authorization",
        "cookie",
        "set-cookie",
        "key",
    }
)


def is_secret_key_name(name: str) -> bool:
    classified = classify_client_control_field(name)
    if classified is not None and classified[1] == CATEGORY_KEY:
        return True
    lowered = str(name).strip().lower().replace("-", "_")
    if lowered in _SECRET_NAME_EXTRAS:
        return True
    if "api_key" in lowered or lowered.endswith("_secret") or lowered.endswith("_token"):
        return True
    return False


def redact_for_log(value: Any) -> Any:
    """Replace secret *values* with [REDACTED]. Keep surrounding structure."""
    if isinstance(value, dict):
        out: dict[str, Any] = {}
        for key, inner in value.items():
            if is_secret_key_name(str(key)):
                out[str(key)] = REDACTED
            else:
                out[str(key)] = redact_for_log(inner)
        return out
    if isinstance(value, list):
        return [redact_for_log(item) for item in value]
    if isinstance(value, tuple):
        return tuple(redact_for_log(item) for item in value)
    return value


def strip_secrets_from_public(value: Any) -> Any:
    """Drop secret keys entirely from a public JSON payload."""
    if isinstance(value, dict):
        return {
            key: strip_secrets_from_public(inner)
            for key, inner in value.items()
            if not is_secret_key_name(str(key))
        }
    if isinstance(value, list):
        return [strip_secrets_from_public(item) for item in value]
    return value


def public_payload_leaks_secret_names(payload: Any) -> list[str]:
    hits: set[str] = set()
    if isinstance(payload, dict):
        for key, inner in payload.items():
            if is_secret_key_name(str(key)):
                hits.add(str(key))
            hits.update(public_payload_leaks_secret_names(inner))
    elif isinstance(payload, list):
        for item in payload:
            hits.update(public_payload_leaks_secret_names(item))
    return sorted(hits)


def redact_known_values(text: str, secrets: Iterable[str]) -> str:
    """Remove known secret *values* from a log line. Never echo them."""
    redacted = text
    for secret in secrets:
        if not secret or len(secret) < 4:
            continue
        redacted = redacted.replace(secret, REDACTED)
    return redacted


def settings_secret_values(settings: Any) -> tuple[str, ...]:
    """Collect process secret values for log scrubbing. Do not return these."""
    collected: list[str] = []
    for name in ("fortyguard_api_key", "internal_key"):
        raw = getattr(settings, name, "")
        if isinstance(raw, str) and raw.strip():
            collected.append(raw)
    return tuple(collected)


class SecretLogFilter(logging.Filter):
    """Scrub record messages. Attach to loggers; do not print secrets first."""

    def __init__(self, secrets: Iterable[str] = ()) -> None:
        super().__init__()
        self._secrets = tuple(secret for secret in secrets if secret and len(secret) >= 4)

    def filter(self, record: logging.LogRecord) -> bool:
        record.msg = redact_known_values(str(record.msg), self._secrets)
        if isinstance(record.args, dict):
            record.args = redact_for_log(record.args)
        elif record.args:
            record.args = tuple(redact_for_log(arg) for arg in record.args)
        return True
