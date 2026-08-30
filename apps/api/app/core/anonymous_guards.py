"""In-process anonymous rate, job-quota, serializer, and cache-cap guards.

Not identity. IP is a class, not an account. No login. No vendor I/O.
Hard demo budget remains the financial backstop. Defaults enforce
(availability), they do not enable spend or mount HTTP.
"""

from __future__ import annotations

from collections import deque
from dataclasses import dataclass, field
from threading import Lock
from time import monotonic
from typing import Any, Callable, Literal
from uuid import uuid4

REASON_RATE_LIMITED = "RATE_LIMITED"
REASON_JOB_QUOTA_IN_FLIGHT = "JOB_QUOTA_IN_FLIGHT"
REASON_JOB_QUOTA_STORED = "JOB_QUOTA_STORED"
REASON_JOB_QUOTA_CLASS = "JOB_QUOTA_CLASS"
REASON_CACHE_ENTRY_CAP = "CACHE_ENTRY_CAP"
REASON_CACHE_BYTE_CAP = "CACHE_BYTE_CAP"
REASON_PUBLIC_VENDOR_CACHE_WRITE = "PUBLIC_VENDOR_CACHE_WRITE"
REASON_CLIENT_CACHE_KEY = "CLIENT_CACHE_KEY"
REASON_BODY_TOO_LARGE = "BODY_TOO_LARGE"

DEFAULT_WINDOW_SECONDS = 60.0
DEFAULT_POST_JOBS_PER_WINDOW = 10
DEFAULT_READ_PER_WINDOW = 60
DEFAULT_PLACE_SEARCH_PER_WINDOW = 5
DEFAULT_GEOGRAPHY_RESOLVE_PER_WINDOW = 2
DEFAULT_MAX_IN_FLIGHT = 8
DEFAULT_MAX_STORED = 256
DEFAULT_MAX_IN_FLIGHT_PER_CLASS = 2
DEFAULT_CACHE_MAX_ENTRIES = 256
DEFAULT_CACHE_MAX_BYTES = 32 * 1024 * 1024
DEFAULT_MAX_BODY_BYTES = 64 * 1024

PUBLIC_SERIALIZER_DENYLIST = frozenset(
    {
        "grant",
        "spend_grant",
        "force_live",
        "key",
        "api_key",
        "apikey",
        "fortyguard_api_key",
        "authorized_max_units",
        "allowance_remaining",
        "demo_budget",
        "internal_key",
        "allowance",
        "approved",
        "authorize",
        "authorized",
        "skip_approval",
        "spend_authorized",
        "bypass_limit",
        "operator_override",
    }
)
_DENY_LOWER = frozenset(name.lower() for name in PUBLIC_SERIALIZER_DENYLIST)


@dataclass(frozen=True)
class RateLimitSpec:
    max_events: int
    window_seconds: float = DEFAULT_WINDOW_SECONDS


DEFAULT_ROUTE_LIMITS: dict[str, RateLimitSpec] = {
    "analysis_jobs_post": RateLimitSpec(DEFAULT_POST_JOBS_PER_WINDOW),
    "geometry_get": RateLimitSpec(DEFAULT_READ_PER_WINDOW),
    "areas_get": RateLimitSpec(DEFAULT_READ_PER_WINDOW),
    "place_search": RateLimitSpec(DEFAULT_PLACE_SEARCH_PER_WINDOW),
    "geography_resolve": RateLimitSpec(DEFAULT_GEOGRAPHY_RESOLVE_PER_WINDOW),
    "read": RateLimitSpec(DEFAULT_READ_PER_WINDOW),
    "other": RateLimitSpec(30),
}


@dataclass(frozen=True)
class RateDecision:
    allowed: bool
    reason_code: str | None = None
    retry_after_seconds: int | None = None


@dataclass(frozen=True)
class JobQuotaDecision:
    allowed: bool
    reason_code: str | None = None
    token: str | None = None


@dataclass(frozen=True)
class CachePutDecision:
    allowed: bool
    reason_code: str | None = None


def classify_route(method: str, path: str) -> str:
    verb = method.upper()
    normalized = path.split("?", 1)[0].rstrip("/") or "/"
    if verb == "POST" and normalized.endswith("/analysis/jobs"):
        return "analysis_jobs_post"
    if "/places" in normalized:
        return "place_search"
    if "/geographies" in normalized:
        return "geography_resolve"
    if normalized.endswith("/geometry") or "/geometry" in normalized:
        return "geometry_get"
    if normalized.endswith("/areas"):
        return "areas_get"
    if verb == "GET":
        return "read"
    return "other"


def client_class_from_headers(headers: dict[str, str]) -> str:
    """IP is a class, not an account. Spoofable headers stay a class only."""
    lowered = {str(key).lower(): str(value) for key, value in headers.items()}
    forwarded = lowered.get("x-forwarded-for", "")
    if forwarded.strip():
        return forwarded.split(",")[0].strip() or "unknown"
    real_ip = lowered.get("x-real-ip", "").strip()
    if real_ip:
        return real_ip
    return lowered.get("client-class", "unknown") or "unknown"


def public_payload_hits_denylist(payload: Any) -> list[str]:
    """Walk a public JSON mapping. Hits are serializer key names, not values."""
    hits: set[str] = set()
    for key in _walk_keys(payload):
        if key.lower() in _DENY_LOWER:
            hits.add(key)
    return sorted(hits)


def strip_denied_public_fields(payload: Any) -> Any:
    """Drop denylist keys. Does not authorize spend. Does not invent fields."""
    if isinstance(payload, dict):
        return {
            key: strip_denied_public_fields(inner)
            for key, inner in payload.items()
            if str(key).lower() not in _DENY_LOWER
        }
    if isinstance(payload, list):
        return [strip_denied_public_fields(item) for item in payload]
    return payload


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


def public_path_may_write_vendor_cache() -> bool:
    """Public request path never writes a vendor cache."""
    return False


def spend_defaults_remain_closed() -> bool:
    """Settings field defaults — not env — keep hosted live off and cap at 0."""
    from app.core.config import Settings

    fields = Settings.model_fields
    return (
        fields["demo_allowance_enabled"].default is False
        and int(fields["demo_allowance_max_total_units"].default) == 0
    )


class InProcessRateLimiter:
    """Sliding-window QPS. Enforcing by default. Not a login quota."""

    def __init__(
        self,
        specs: dict[str, RateLimitSpec] | None = None,
        *,
        now: Callable[[], float] | None = None,
    ) -> None:
        self._specs = dict(specs or DEFAULT_ROUTE_LIMITS)
        self._hits: dict[tuple[str, str], deque[float]] = {}
        self._lock = Lock()
        self._now = now or monotonic

    def allow(self, *, route_class: str, client_class: str) -> RateDecision:
        spec = self._specs.get(route_class) or self._specs.get("other") or RateLimitSpec(30)
        key = (route_class, client_class)
        now = self._now()
        cutoff = now - spec.window_seconds
        with self._lock:
            bucket = self._hits.setdefault(key, deque())
            while bucket and bucket[0] <= cutoff:
                bucket.popleft()
            if len(bucket) >= spec.max_events:
                oldest = bucket[0]
                retry = max(1, int(spec.window_seconds - (now - oldest) + 0.999))
                return RateDecision(
                    allowed=False,
                    reason_code=REASON_RATE_LIMITED,
                    retry_after_seconds=retry,
                )
            bucket.append(now)
            return RateDecision(allowed=True)


class InProcessJobQuota:
    """Process-local create cap. Evicts only terminal slots. Never identity."""

    def __init__(
        self,
        *,
        max_in_flight: int = DEFAULT_MAX_IN_FLIGHT,
        max_stored: int = DEFAULT_MAX_STORED,
        max_in_flight_per_class: int = DEFAULT_MAX_IN_FLIGHT_PER_CLASS,
    ) -> None:
        if max_in_flight < 1 or max_stored < 1 or max_in_flight_per_class < 1:
            raise ValueError("job quota caps must be positive")
        self.max_in_flight = max_in_flight
        self.max_stored = max_stored
        self.max_in_flight_per_class = max_in_flight_per_class
        self._in_flight: dict[str, str] = {}
        self._class_in_flight: dict[str, int] = {}
        self._stored = 0
        self._lock = Lock()

    @property
    def in_flight_count(self) -> int:
        with self._lock:
            return len(self._in_flight)

    @property
    def stored_count(self) -> int:
        with self._lock:
            return self._stored

    def try_create(self, client_class: str) -> JobQuotaDecision:
        with self._lock:
            if self._stored >= self.max_stored:
                return JobQuotaDecision(False, REASON_JOB_QUOTA_STORED)
            if len(self._in_flight) >= self.max_in_flight:
                return JobQuotaDecision(False, REASON_JOB_QUOTA_IN_FLIGHT)
            used = self._class_in_flight.get(client_class, 0)
            if used >= self.max_in_flight_per_class:
                return JobQuotaDecision(False, REASON_JOB_QUOTA_CLASS)
            token = f"jq_{uuid4().hex[:12]}"
            self._in_flight[token] = client_class
            self._class_in_flight[client_class] = used + 1
            self._stored += 1
            return JobQuotaDecision(True, None, token)

    def mark_terminal(self, token: str) -> None:
        """Release in-flight. Stored count stays until evict_oldest_terminal."""
        with self._lock:
            client = self._in_flight.pop(token, None)
            if client is None:
                return
            remaining = self._class_in_flight.get(client, 1) - 1
            if remaining <= 0:
                self._class_in_flight.pop(client, None)
            else:
                self._class_in_flight[client] = remaining

    def evict_oldest_terminal_slot(self) -> bool:
        """Drop one terminal stored slot. Never evicts in-flight work."""
        with self._lock:
            terminal = self._stored - len(self._in_flight)
            if terminal <= 0:
                return False
            self._stored -= 1
            return True


class CacheCapPolicy:
    """Byte/count caps. Public path never writes a vendor cache."""

    def __init__(
        self,
        *,
        max_entries: int = DEFAULT_CACHE_MAX_ENTRIES,
        max_bytes: int = DEFAULT_CACHE_MAX_BYTES,
        allow_public_vendor_writes: bool = False,
    ) -> None:
        del allow_public_vendor_writes
        self.max_entries = max_entries
        self.max_bytes = max_bytes
        self.allow_public_vendor_writes = False

    def decide_put(
        self,
        *,
        path: Literal["public", "internal"],
        vendor: bool,
        entry_count: int,
        used_bytes: int,
        incoming_bytes: int,
        client_supplied_key: str | None = None,
    ) -> CachePutDecision:
        if vendor and path == "public" and not public_path_may_write_vendor_cache():
            return CachePutDecision(False, REASON_PUBLIC_VENDOR_CACHE_WRITE)
        if client_supplied_key:
            return CachePutDecision(False, REASON_CLIENT_CACHE_KEY)
        if incoming_bytes < 0 or used_bytes < 0 or entry_count < 0:
            return CachePutDecision(False, REASON_CACHE_BYTE_CAP)
        if entry_count >= self.max_entries:
            return CachePutDecision(False, REASON_CACHE_ENTRY_CAP)
        if used_bytes + incoming_bytes > self.max_bytes:
            return CachePutDecision(False, REASON_CACHE_BYTE_CAP)
        return CachePutDecision(True)


@dataclass
class AnonymousGuards:
    """Default-safe bundle. Constructing this does not mount HTTP or spend."""

    limiter: InProcessRateLimiter = field(default_factory=InProcessRateLimiter)
    quota: InProcessJobQuota = field(default_factory=InProcessJobQuota)
    cache: CacheCapPolicy = field(default_factory=CacheCapPolicy)
    max_body_bytes: int = DEFAULT_MAX_BODY_BYTES
