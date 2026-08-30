"""Always-on public-safety ASGI middleware.

Rejects forbidden control fields from header, query, and body.
Does not authorize spend. Does not enable hosted live.
Client cannot disable this. Operator may disable via process env only.
"""

from __future__ import annotations

import json
import os
from typing import Any
from urllib.parse import parse_qs

from starlette.responses import JSONResponse
from starlette.types import ASGIApp, Receive, Scope, Send

from app.core.public_safety import (
    REASON_CLIENT_FORBIDDEN_FIELD,
    scan_client_request,
    rejection_payload,
)
from app.services.secret_redaction import strip_secrets_from_public

PUBLIC_SAFETY_MIDDLEWARE_ENV = "HVA_PUBLIC_SAFETY_MIDDLEWARE"
DEFAULT_MAX_BODY_BYTES = 64 * 1024


def public_safety_middleware_enabled() -> bool:
    """Default ON. Server env only. Client headers cannot disable this."""
    raw = os.environ.get(PUBLIC_SAFETY_MIDDLEWARE_ENV, "1").strip().lower()
    return raw not in {"0", "false", "no", "off"}


def _header_map(scope: Scope) -> dict[str, str]:
    raw = scope.get("headers") or []
    out: dict[str, str] = {}
    for key, value in raw:
        out[key.decode("latin-1")] = value.decode("latin-1")
    return out


async def _read_body(receive: Receive) -> bytes:
    chunks: list[bytes] = []
    while True:
        message = await receive()
        chunks.append(message.get("body", b"") or b"")
        if not message.get("more_body"):
            break
    return b"".join(chunks)


def _replay(body: bytes) -> Receive:
    sent = False

    async def receive() -> dict[str, Any]:
        nonlocal sent
        if sent:
            return {"type": "http.disconnect"}
        sent = True
        return {"type": "http.request", "body": body, "more_body": False}

    return receive


def _parse_body(body: bytes, content_type: str) -> Any:
    if not body:
        return None
    lowered = content_type.split(";", 1)[0].strip().lower()
    if lowered in {"application/json", "text/json", "application/problem+json"}:
        try:
            return json.loads(body.decode("utf-8"))
        except (UnicodeDecodeError, json.JSONDecodeError):
            return None
    if lowered == "application/x-www-form-urlencoded":
        try:
            return parse_qs(body.decode("utf-8"), keep_blank_values=True)
        except UnicodeDecodeError:
            return None
    return None


class PublicSafetyMiddleware:
    """Reject client control-plane fields. Always on unless operator env disables."""

    def __init__(
        self,
        app: ASGIApp,
        *,
        enabled: bool | None = None,
        max_body_bytes: int = DEFAULT_MAX_BODY_BYTES,
    ) -> None:
        self.app = app
        self.enabled = (
            public_safety_middleware_enabled() if enabled is None else enabled
        )
        self.max_body_bytes = max_body_bytes

    async def __call__(self, scope: Scope, receive: Receive, send: Send) -> None:
        if scope["type"] != "http" or not self.enabled:
            await self.app(scope, receive, send)
            return

        headers = _header_map(scope)
        query = scope.get("query_string") or b""
        method = str(scope.get("method") or "GET").upper()
        content_type = headers.get("content-type", "")
        body = b""
        parsed_body: Any = None
        if method in {"POST", "PUT", "PATCH", "DELETE"}:
            body = await _read_body(receive)
            if len(body) > self.max_body_bytes:
                await JSONResponse(
                    {"reason_code": "BODY_TOO_LARGE"},
                    status_code=413,
                )(scope, receive, send)
                return
            parsed_body = _parse_body(body, content_type)
            receive = _replay(body)

        hits = scan_client_request(
            headers=headers,
            query=query,
            body=parsed_body,
        )
        if hits:
            payload = strip_secrets_from_public(rejection_payload(hits))
            await JSONResponse(payload, status_code=422)(scope, receive, send)
            return

        await self.app(scope, receive, send)


def install_public_safety(app: Any, *, enabled: bool | None = None) -> None:
    """Mount public-safety middleware. Safe to call from app factory."""
    app.add_middleware(PublicSafetyMiddleware, enabled=enabled)
