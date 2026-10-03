"""httpx FortyGuard client. Auth is an `api-key` header, not Bearer.

Analytical engines must not import this module to call FortyGuard.
"""

from __future__ import annotations

import math
import time
from collections.abc import Callable
from typing import Any, TYPE_CHECKING

if TYPE_CHECKING:
    from app.core.postgres_acquisition import PostgresAcquisitionStore

import httpx

from app.integrations.fortyguard.exceptions import (
    ActivityNotReadyError,
    FortyGuardHttpError,
    MissingApiKeyError,
)
from app.integrations.fortyguard.polling import wait_for

DEFAULT_BASE_URL = "https://api.fortyguard.com"


class FortyGuardHttpClient:
    """Thin HTTP client. The API key is sent only as the `api-key` header."""

    def __init__(
        self,
        api_key: str | None,
        *,
        base_url: str = DEFAULT_BASE_URL,
        timeout: float = 60.0,
        transport: httpx.BaseTransport | None = None,
        before_submit: Callable[[], None] | None = None,
        acquisition_store: PostgresAcquisitionStore | None = None,
    ) -> None:
        if not api_key or not str(api_key).strip():
            raise MissingApiKeyError(
                "LIVE FortyGuard access requires FORTYGUARD_API_KEY on the backend."
            )
        headers = {
            "api-key": str(api_key).strip(),
            "Content-Type": "application/json",
        }
        kwargs: dict[str, Any] = {
            "base_url": base_url.rstrip("/"),
            "headers": headers,
            "timeout": timeout,
        }
        if transport is not None:
            kwargs["transport"] = transport
        self._client = httpx.Client(**kwargs)
        self._api_key = str(api_key).strip()
        self._before_submit = before_submit
        self._acquisition_store = acquisition_store
        self.last_acquisition_source = "live"
        self.submission_count = 0
        self.status_lookup_count = 0

    def close(self) -> None:
        self._client.close()

    def __enter__(self) -> FortyGuardHttpClient:
        return self

    def __exit__(self, *exc: object) -> None:
        self.close()

    def _raise_for_status(self, method: str, path: str, resp: httpx.Response) -> None:
        if resp.is_success:
            return
        raise FortyGuardHttpError(
            f"{method} {path} -> {resp.status_code}: {resp.text[:500]}",
            status_code=resp.status_code,
        )

    def submit(self, path: str, payload: dict[str, Any]) -> str:
        if self._acquisition_store is not None:
            raise RuntimeError("Durable acquisitions must use submit_and_wait.")
        return self._submit_raw(path, payload)

    def _submit_raw(self, path: str, payload: dict[str, Any]) -> str:
        if self._before_submit is not None:
            self._before_submit()
        self.submission_count += 1
        resp = self._client.post(path, json=payload)
        self._raise_for_status("POST", path, resp)
        try:
            body = resp.json()
        except ValueError as exc:
            raise FortyGuardHttpError(f"POST {path} returned non-JSON") from exc
        if body.get("error"):
            raise FortyGuardHttpError(body.get("message", "Submission failed"))
        try:
            activity_id = body["data"]["activity_id"]
        except (KeyError, TypeError) as exc:
            raise FortyGuardHttpError(f"Unexpected submit shape: {body}") from exc
        if not isinstance(activity_id, str) or not activity_id.strip():
            raise FortyGuardHttpError("Submission returned no usable activity ID")
        return activity_id

    def remaining_credits(self) -> float:
        """Return only the numeric balance from the provider's usage response."""
        path = "/v1/system/fetch-api-key-usage"
        response = self._client.post(path, json={"api_key": self._api_key})
        # Do not include the response body: providers may echo submitted credentials.
        if not response.is_success:
            raise FortyGuardHttpError("Credit usage lookup failed", status_code=response.status_code)
        try:
            body = response.json()
            summary = body.get("credit_summary")
            if not isinstance(summary, dict):
                summary = body.get("data", {}).get("credit_summary")
            remaining = summary.get("cycle_remaining_credits")
            if remaining is None:
                remaining = summary.get("total_remaining_credits")
            if isinstance(remaining, bool) or not isinstance(remaining, (int, float)) or not math.isfinite(remaining) or remaining < 0:
                raise ValueError("Invalid balance")
            return float(remaining)
        except (ValueError, TypeError, AttributeError):
            raise FortyGuardHttpError("Credit usage response has no valid numeric balance") from None

    def get_status(self, activity_id: str) -> dict[str, Any]:
        self.status_lookup_count += 1
        path = f"/v1/status/{activity_id}"
        resp = self._client.get(path)
        if resp.status_code == 404:
            raise ActivityNotReadyError(activity_id)
        self._raise_for_status("GET", path, resp)
        body = resp.json()
        if body.get("error"):
            raise FortyGuardHttpError(body.get("message", "Status lookup failed"))
        try:
            return dict(body["data"])
        except (KeyError, TypeError) as exc:
            raise FortyGuardHttpError(f"Unexpected status shape: {body}") from exc

    def submit_and_wait(
        self,
        path: str,
        payload: dict[str, Any],
        *,
        poll_interval: float = 3.0,
        timeout: float = 600.0,
        sleep: Callable[[float], None] = time.sleep,
        monotonic: Callable[[], float] = time.monotonic,
    ) -> dict[str, Any]:
        def poll(activity_id: str) -> dict[str, Any]:
            return wait_for(
                self.get_status, activity_id, poll_interval=poll_interval,
                timeout=timeout, sleep=sleep, monotonic=monotonic,
            )

        if self._acquisition_store is not None:
            bundled, self.last_acquisition_source = self._acquisition_store.run(
                path, payload, submit=lambda: self._submit_raw(path, payload), poll=poll,
            )
            return bundled
        self.last_acquisition_source = "live"
        activity_id = self.submit(path, payload)
        result = poll(activity_id)
        return {"activity_id": activity_id, "result": result}
