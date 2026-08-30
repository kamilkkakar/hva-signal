"""Scan client body, query, and headers for forbidden control-plane fields.

Rejects — does not strip-and-continue. Values are never echoed.
No vendor I/O. No FortyGuard import.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Iterable, Literal
from urllib.parse import parse_qs

from app.domain.public_safety_fields import (
    classify_client_control_field,
)

REASON_CLIENT_FORBIDDEN_FIELD = "CLIENT_FORBIDDEN_FIELD"
Surface = Literal["body", "query", "header"]


@dataclass(frozen=True)
class ForbiddenHit:
    raw_name: str
    canonical: str
    category: str
    surface: Surface


def walk_keys(value: Any) -> list[str]:
    found: list[str] = []
    if isinstance(value, dict):
        for key, inner in value.items():
            found.append(str(key))
            found.extend(walk_keys(inner))
    elif isinstance(value, (list, tuple)):
        for item in value:
            found.extend(walk_keys(item))
    return found


def scan_mapping(payload: Any, *, surface: Surface) -> list[ForbiddenHit]:
    hits: list[ForbiddenHit] = []
    seen: set[tuple[str, str, str]] = set()
    for raw in walk_keys(payload):
        classified = classify_client_control_field(raw)
        if classified is None:
            continue
        canonical, category = classified
        marker = (raw, canonical, surface)
        if marker in seen:
            continue
        seen.add(marker)
        hits.append(
            ForbiddenHit(
                raw_name=raw,
                canonical=canonical,
                category=category,
                surface=surface,
            )
        )
    return hits


def scan_headers(headers: dict[str, str] | Iterable[tuple[str, str]]) -> list[ForbiddenHit]:
    # Classify header *names* only. Values are never returned or logged here.
    names = (
        headers.keys()
        if isinstance(headers, dict)
        else (key for key, _value in headers)
    )
    return scan_mapping({str(name): True for name in names}, surface="header")


def scan_query(query: dict[str, Any] | str | bytes) -> list[ForbiddenHit]:
    if isinstance(query, (bytes, bytearray)):
        query = query.decode("latin-1")
    if isinstance(query, str):
        parsed = parse_qs(query, keep_blank_values=True)
        return scan_mapping(parsed, surface="query")
    return scan_mapping(query, surface="query")


def scan_client_request(
    *,
    headers: dict[str, str] | None = None,
    query: dict[str, Any] | str | bytes | None = None,
    body: Any = None,
) -> list[ForbiddenHit]:
    hits: list[ForbiddenHit] = []
    if headers:
        hits.extend(scan_headers(headers))
    if query is not None and query != "":
        hits.extend(scan_query(query))
    if body is not None:
        hits.extend(scan_mapping(body, surface="body"))
    return hits


def rejection_payload(hits: list[ForbiddenHit]) -> dict[str, Any]:
    """Public error body. Field *names* and categories only — never values."""
    return {
        "reason_code": REASON_CLIENT_FORBIDDEN_FIELD,
        "categories": sorted({hit.category for hit in hits}),
        "fields": sorted({hit.canonical for hit in hits}),
        "surfaces": sorted({hit.surface for hit in hits}),
    }
