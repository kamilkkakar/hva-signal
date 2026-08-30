"""Optional anonymous guard ASGI middleware. Gated OFF by default.

Mounting is opt-in. This module does not import main.py and does not
enable demo allowance or construct a vendor adapter.
"""

from __future__ import annotations

import os
from typing import Any

from starlette.responses import JSONResponse
from starlette.types import ASGIApp, Receive, Scope, Send

from app.core.anonymous_guards import (
    DEFAULT_MAX_BODY_BYTES,
    REASON_BODY_TOO_LARGE,
    REASON_RATE_LIMITED,
    AnonymousGuards,
    classify_route,
    client_class_from_headers,
)

GUARD_MIDDLEWARE_ENV = "ANONYMOUS_GUARD_MIDDLEWARE"


def anonymous_guard_middleware_enabled() -> bool:
    """Server env only. Client headers cannot enable this."""
    raw = os.environ.get(GUARD_MIDDLEWARE_ENV, "").strip().lower()
    return raw in {"1", "true", "yes", "on"}


def _header_map(scope: Scope) -> dict[str, str]:
    raw = scope.get("headers") or []
    out: dict[str, str] = {}
    for key, value in raw:
        out[key.decode("latin-1")] = value.decode("latin-1")
    return out


class AnonymousGuardMiddleware:
    """Rate-limit + body-size + job-quota. No login wall. No spend grant."""

    def __init__(
        self,
        app: ASGIApp,
        *,
        enabled: bool | None = None,
        guards: AnonymousGuards | None = None,
        max_body_bytes: int | None = None,
    ) -> None:
        self.app = app
        self.enabled = (
            anonymous_guard_middleware_enabled() if enabled is None else enabled
        )
        self.guards = guards or AnonymousGuards()
        self.max_body_bytes = (
            self.guards.max_body_bytes if max_body_bytes is None else max_body_bytes
        )

    async def __call__(self, scope: Scope, receive: Receive, send: Send) -> None:
        if scope["type"] != "http" or not self.enabled:
            await self.app(scope, receive, send)
            return

        method = str(scope.get("method") or "GET")
        path = str(scope.get("path") or "/")
        headers = _header_map(scope)
        content_length = headers.get("content-length")
        if content_length is not None:
            try:
                size = int(content_length)
            except ValueError:
                size = -1
            if size < 0 or size > self.max_body_bytes:
                await _json(
                    status_code=413,
                    reason_code=REASON_BODY_TOO_LARGE,
                )(scope, receive, send)
                return

        route_class = classify_route(method, path)
        client_class = client_class_from_headers(headers)
        rate = self.guards.limiter.allow(
            route_class=route_class,
            client_class=client_class,
        )
        if not rate.allowed:
            await _json(
                status_code=429,
                reason_code=rate.reason_code or REASON_RATE_LIMITED,
                retry_after=rate.retry_after_seconds,
            )(scope, receive, send)
            return

        if route_class == "analysis_jobs_post":
            quota = self.guards.quota.try_create(client_class)
            if not quota.allowed:
                await _json(
                    status_code=429,
                    reason_code=quota.reason_code or REASON_RATE_LIMITED,
                    retry_after=60,
                )(scope, receive, send)
                return

        await self.app(scope, receive, send)


def _json(
    *,
    status_code: int,
    reason_code: str,
    retry_after: int | None = None,
) -> JSONResponse:
    headers: dict[str, str] = {}
    if retry_after is not None:
        headers["Retry-After"] = str(retry_after)
    payload: dict[str, Any] = {"reason_code": reason_code}
    return JSONResponse(payload, status_code=status_code, headers=headers)
