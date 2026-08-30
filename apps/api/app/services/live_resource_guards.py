"""Server-side rate, concurrency, and resource guards for hosted-live acquire.

Caps apply to reserve / submit / recovery-poll only. They never authorize
spend, never construct a vendor, and never read credentials.

Operator env may LOWER a cap. It cannot raise a cap above the hard ceiling.
Client body, query, and headers cannot set or raise any cap.
"""

from __future__ import annotations

import os
from collections import deque
from dataclasses import dataclass, field
from threading import Lock
from time import monotonic
from typing import Any, Callable, Literal
from uuid import uuid4

REASON_RATE_LIMITED = "LIVE_RATE_LIMITED"
REASON_RESERVE_CAP = "LIVE_RESERVE_CAP"
REASON_SUBMIT_CAP = "LIVE_SUBMIT_CAP"
REASON_IN_FLIGHT_CAP = "LIVE_IN_FLIGHT_CAP"
REASON_RECOVERY_POLL_CAP = "LIVE_RECOVERY_POLL_CAP"
REASON_BACKPRESSURE = "LIVE_BACKPRESSURE"
REASON_QUEUED = "LIVE_QUEUED"
REASON_CLIENT_CAP_OVERRIDE = "LIVE_CLIENT_CANNOT_RAISE_CAPS"
REASON_CLOSED = "LIVE_RESOURCE_CLOSED"

ACTION_RESERVE = "reserve"
ACTION_SUBMIT = "submit"
ACTION_RECOVERY_POLL = "recovery_poll"

# Hard ceilings. Operator env is clamped to these. Client input is ignored.
CEILING_MAX_IN_FLIGHT_JOBS = 2
CEILING_MAX_RESERVATIONS = 2
CEILING_MAX_CONCURRENT_SUBMITS = 1
CEILING_MAX_RECOVERY_POLLS_PER_ACTIVITY = 16
CEILING_MAX_RECOVERY_POLLS_PER_WINDOW = 24
CEILING_RESERVE_PER_WINDOW = 4
CEILING_SUBMIT_PER_WINDOW = 2
CEILING_QUEUE_DEPTH = 4
CEILING_WINDOW_SECONDS = 60.0

DEFAULT_WINDOW_SECONDS = 60.0

OPERATOR_ENV = {
    "HVA_LIVE_MAX_IN_FLIGHT_JOBS": "max_in_flight_jobs",
    "HVA_LIVE_MAX_RESERVATIONS": "max_reservations",
    "HVA_LIVE_MAX_CONCURRENT_SUBMITS": "max_concurrent_submits",
    "HVA_LIVE_MAX_RECOVERY_POLLS_PER_ACTIVITY": "max_recovery_polls_per_activity",
    "HVA_LIVE_MAX_RECOVERY_POLLS_PER_WINDOW": "max_recovery_polls_per_window",
    "HVA_LIVE_RESERVE_PER_WINDOW": "reserve_per_window",
    "HVA_LIVE_SUBMIT_PER_WINDOW": "submit_per_window",
    "HVA_LIVE_QUEUE_DEPTH": "queue_depth",
}

CLIENT_FORBIDDEN_LIMIT_KEYS = frozenset(
    {
        "max_in_flight",
        "max_in_flight_jobs",
        "max_reservations",
        "max_recovery_polls",
        "max_recovery_polls_per_activity",
        "max_recovery_polls_per_window",
        "rate_limit",
        "rate_limit_per_window",
        "reserve_per_window",
        "submit_per_window",
        "concurrency",
        "concurrency_cap",
        "max_concurrent_submits",
        "queue_depth",
        "submit_cap",
        "reserve_cap",
        "backpressure",
        "resource_cap",
        "poll_budget",
        "retry_budget",
        "live_max_in_flight",
        "live_max_reservations",
        "bypass_limit",
        "bypass_rate_limit",
        "bypass_resource_guard",
    }
)
_CLIENT_FORBIDDEN_LOWER = frozenset(name.lower() for name in CLIENT_FORBIDDEN_LIMIT_KEYS)

_CLIENT_HEADER_PREFIXES = (
    "x-max-",
    "x-rate",
    "x-concurrency",
    "x-queue",
    "x-backpressure",
    "x-resource-",
    "x-poll-budget",
)

OpKind = Literal["reserve", "submit", "recovery_poll"]


@dataclass(frozen=True)
class LiveResourceLimits:
    """Process limits after ceiling clamp. Not a client type."""

    max_in_flight_jobs: int = CEILING_MAX_IN_FLIGHT_JOBS
    max_reservations: int = CEILING_MAX_RESERVATIONS
    max_concurrent_submits: int = CEILING_MAX_CONCURRENT_SUBMITS
    max_recovery_polls_per_activity: int = CEILING_MAX_RECOVERY_POLLS_PER_ACTIVITY
    max_recovery_polls_per_window: int = CEILING_MAX_RECOVERY_POLLS_PER_WINDOW
    reserve_per_window: int = CEILING_RESERVE_PER_WINDOW
    submit_per_window: int = CEILING_SUBMIT_PER_WINDOW
    queue_depth: int = CEILING_QUEUE_DEPTH
    window_seconds: float = DEFAULT_WINDOW_SECONDS

    def as_public_note(self) -> dict[str, int | float]:
        return {
            "max_in_flight_jobs": self.max_in_flight_jobs,
            "max_reservations": self.max_reservations,
            "max_concurrent_submits": self.max_concurrent_submits,
            "max_recovery_polls_per_activity": self.max_recovery_polls_per_activity,
            "max_recovery_polls_per_window": self.max_recovery_polls_per_window,
            "reserve_per_window": self.reserve_per_window,
            "submit_per_window": self.submit_per_window,
            "queue_depth": self.queue_depth,
            "window_seconds": self.window_seconds,
        }


@dataclass(frozen=True)
class Admission:
    """Whether the caller may touch reserve / mock / future vendor."""

    allowed: bool
    reason_code: str | None = None
    token: str | None = None
    queued: bool = False
    retry_after_seconds: int | None = None

    @property
    def proceed(self) -> bool:
        """True only when reserve/submit/poll may run now. Queued is not proceed."""
        return self.allowed and not self.queued


@dataclass(frozen=True)
class QueuedWork:
    kind: OpKind
    token: str
    enqueued_at: float


def _clamp_int(value: int, *, ceiling: int) -> int:
    if value < 0:
        return 0
    return min(int(value), ceiling)


def _clamp_window(value: float) -> float:
    if value <= 0:
        return DEFAULT_WINDOW_SECONDS
    return min(float(value), CEILING_WINDOW_SECONDS)


def clamp_operator_limits(
    proposed: LiveResourceLimits | dict[str, Any] | None = None,
) -> LiveResourceLimits:
    """Operator/server values only. Anything above a ceiling is silently cut."""
    if proposed is None:
        return LiveResourceLimits()
    if isinstance(proposed, LiveResourceLimits):
        data = proposed.as_public_note()
    else:
        data = dict(proposed)
    return LiveResourceLimits(
        max_in_flight_jobs=_clamp_int(
            int(data.get("max_in_flight_jobs", CEILING_MAX_IN_FLIGHT_JOBS)),
            ceiling=CEILING_MAX_IN_FLIGHT_JOBS,
        ),
        max_reservations=_clamp_int(
            int(data.get("max_reservations", CEILING_MAX_RESERVATIONS)),
            ceiling=CEILING_MAX_RESERVATIONS,
        ),
        max_concurrent_submits=_clamp_int(
            int(data.get("max_concurrent_submits", CEILING_MAX_CONCURRENT_SUBMITS)),
            ceiling=CEILING_MAX_CONCURRENT_SUBMITS,
        ),
        max_recovery_polls_per_activity=_clamp_int(
            int(
                data.get(
                    "max_recovery_polls_per_activity",
                    CEILING_MAX_RECOVERY_POLLS_PER_ACTIVITY,
                )
            ),
            ceiling=CEILING_MAX_RECOVERY_POLLS_PER_ACTIVITY,
        ),
        max_recovery_polls_per_window=_clamp_int(
            int(
                data.get(
                    "max_recovery_polls_per_window",
                    CEILING_MAX_RECOVERY_POLLS_PER_WINDOW,
                )
            ),
            ceiling=CEILING_MAX_RECOVERY_POLLS_PER_WINDOW,
        ),
        reserve_per_window=_clamp_int(
            int(data.get("reserve_per_window", CEILING_RESERVE_PER_WINDOW)),
            ceiling=CEILING_RESERVE_PER_WINDOW,
        ),
        submit_per_window=_clamp_int(
            int(data.get("submit_per_window", CEILING_SUBMIT_PER_WINDOW)),
            ceiling=CEILING_SUBMIT_PER_WINDOW,
        ),
        queue_depth=_clamp_int(
            int(data.get("queue_depth", CEILING_QUEUE_DEPTH)),
            ceiling=CEILING_QUEUE_DEPTH,
        ),
        window_seconds=_clamp_window(
            float(data.get("window_seconds", DEFAULT_WINDOW_SECONDS))
        ),
    )


def limits_from_operator_env(
    environ: dict[str, str] | None = None,
) -> LiveResourceLimits:
    source = environ if environ is not None else os.environ
    proposed: dict[str, Any] = {}
    for env_name, field_name in OPERATOR_ENV.items():
        raw = source.get(env_name)
        if raw is None or str(raw).strip() == "":
            continue
        proposed[field_name] = int(str(raw).strip())
    return clamp_operator_limits(proposed or None)


def client_limit_override_keys(payload: Any) -> list[str]:
    """Walk untrusted JSON. Hits are keys the client is forbidden to set."""
    hits: set[str] = set()
    for key in _walk_keys(payload):
        if key.lower() in _CLIENT_FORBIDDEN_LOWER:
            hits.add(key)
    return sorted(hits)


def headers_attempt_limit_override(headers: dict[str, str]) -> list[str]:
    hits: set[str] = set()
    for raw_key in headers:
        key = str(raw_key).lower()
        dashed = key.replace("_", "-")
        if key.replace("-", "_") in _CLIENT_FORBIDDEN_LOWER:
            hits.add(raw_key)
            continue
        if any(dashed.startswith(prefix) for prefix in _CLIENT_HEADER_PREFIXES):
            hits.add(raw_key)
    return sorted(hits)


def refuse_client_limit_override(
    payload: Any = None,
    headers: dict[str, str] | None = None,
) -> list[str]:
    """Return forbidden keys. Non-empty means do not admit and do not raise caps."""
    hits = set(client_limit_override_keys(payload))
    if headers:
        hits.update(headers_attempt_limit_override(headers))
    return sorted(hits)


def limits_from_untrusted(
    payload: Any = None,
    headers: dict[str, str] | None = None,
    *,
    operator: LiveResourceLimits | None = None,
) -> tuple[LiveResourceLimits, list[str]]:
    """Client values are ignored. Returned limits are server/operator only."""
    hits = refuse_client_limit_override(payload, headers)
    return (operator or clamp_operator_limits(None), hits)


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


class LiveResourceGuards:
    """Process-local admit/queue for reserve, submit, and recovery polls.

    Constructing this does not mount HTTP, enable hosted live, or spend.
    """

    def __init__(
        self,
        limits: LiveResourceLimits | None = None,
        *,
        now: Callable[[], float] | None = None,
    ) -> None:
        self.limits = clamp_operator_limits(limits)
        self._now = now or monotonic
        self._lock = Lock()
        self._reserve_hits: deque[float] = deque()
        self._submit_hits: deque[float] = deque()
        self._recovery_hits: deque[float] = deque()
        self._reservations: dict[str, str] = {}
        self._in_flight: dict[str, str] = {}
        self._submits: dict[str, str] = {}
        self._polls_by_activity: dict[str, int] = {}
        self._queue: deque[QueuedWork] = deque()

    @property
    def reservation_count(self) -> int:
        with self._lock:
            return len(self._reservations)

    @property
    def in_flight_count(self) -> int:
        with self._lock:
            return len(self._in_flight)

    @property
    def concurrent_submit_count(self) -> int:
        with self._lock:
            return len(self._submits)

    @property
    def queue_count(self) -> int:
        with self._lock:
            return len(self._queue)

    def admit_reserve(
        self,
        *,
        join_existing: bool = False,
        payload: Any = None,
        headers: dict[str, str] | None = None,
    ) -> Admission:
        """Admit a NEW reservation. Joins do not consume a slot or rate token."""
        override = refuse_client_limit_override(payload, headers)
        if override:
            return Admission(False, REASON_CLIENT_CAP_OVERRIDE)
        if join_existing:
            return Admission(True)
        with self._lock:
            return self._admit_reserve_unlocked()

    def release_reserve(self, token: str) -> None:
        with self._lock:
            self._reservations.pop(token, None)

    def admit_submit(
        self,
        *,
        payload: Any = None,
        headers: dict[str, str] | None = None,
    ) -> Admission:
        override = refuse_client_limit_override(payload, headers)
        if override:
            return Admission(False, REASON_CLIENT_CAP_OVERRIDE)
        with self._lock:
            return self._admit_submit_unlocked()

    def finish_submit_rpc(self, token: str) -> None:
        """Release the concurrent-submit slot. In-flight job stays until complete."""
        with self._lock:
            self._submits.pop(token, None)

    def complete_job(self, token: str) -> None:
        with self._lock:
            self._submits.pop(token, None)
            self._in_flight.pop(token, None)

    def admit_recovery_poll(
        self,
        activity_id: str,
        *,
        payload: Any = None,
        headers: dict[str, str] | None = None,
    ) -> Admission:
        override = refuse_client_limit_override(payload, headers)
        if override:
            return Admission(False, REASON_CLIENT_CAP_OVERRIDE)
        if not activity_id:
            return Admission(False, REASON_RECOVERY_POLL_CAP)
        with self._lock:
            return self._admit_recovery_unlocked(activity_id)

    def reset_recovery_polls(self, activity_id: str) -> None:
        with self._lock:
            self._polls_by_activity.pop(activity_id, None)

    def promote(self) -> Admission | None:
        """If a queued item can run now, admit it. Does not call a vendor."""
        with self._lock:
            if not self._queue:
                return None
            head = self._queue[0]
            if head.kind == ACTION_RESERVE:
                admitted = self._admit_reserve_unlocked(queue_on_full=False)
            elif head.kind == ACTION_SUBMIT:
                admitted = self._admit_submit_unlocked(queue_on_full=False)
            else:
                return None
            if not admitted.proceed:
                return None
            self._queue.popleft()
            return admitted

    def call_if_admitted(
        self,
        kind: OpKind,
        fn: Callable[[], Any],
        *,
        activity_id: str | None = None,
        payload: Any = None,
        headers: dict[str, str] | None = None,
    ) -> tuple[Admission, Any]:
        """Run fn only after admission. Stampede callers never reach fn."""
        if kind == ACTION_RESERVE:
            admission = self.admit_reserve(payload=payload, headers=headers)
        elif kind == ACTION_SUBMIT:
            admission = self.admit_submit(payload=payload, headers=headers)
        else:
            admission = self.admit_recovery_poll(
                activity_id or "", payload=payload, headers=headers
            )
        if not admission.proceed:
            return admission, None
        try:
            return admission, fn()
        finally:
            if kind == ACTION_SUBMIT and admission.token:
                self.finish_submit_rpc(admission.token)

    def _admit_reserve_unlocked(self, *, queue_on_full: bool = True) -> Admission:
        if self.limits.max_reservations <= 0 or self.limits.reserve_per_window <= 0:
            return Admission(False, REASON_CLOSED)
        if len(self._reservations) >= self.limits.max_reservations:
            return self._queue_or_reject(ACTION_RESERVE, queue_on_full)
        rate = self._take_rate(
            self._reserve_hits,
            max_events=self.limits.reserve_per_window,
            reason=REASON_RATE_LIMITED,
        )
        if rate is not None:
            return rate
        token = f"rsv_{uuid4().hex[:12]}"
        self._reservations[token] = ACTION_RESERVE
        return Admission(True, token=token)

    def _admit_submit_unlocked(self, *, queue_on_full: bool = True) -> Admission:
        if (
            self.limits.max_concurrent_submits <= 0
            or self.limits.max_in_flight_jobs <= 0
            or self.limits.submit_per_window <= 0
        ):
            return Admission(False, REASON_CLOSED)
        if len(self._in_flight) >= self.limits.max_in_flight_jobs:
            return self._queue_or_reject(ACTION_SUBMIT, queue_on_full, REASON_IN_FLIGHT_CAP)
        if len(self._submits) >= self.limits.max_concurrent_submits:
            return self._queue_or_reject(ACTION_SUBMIT, queue_on_full, REASON_SUBMIT_CAP)
        rate = self._take_rate(
            self._submit_hits,
            max_events=self.limits.submit_per_window,
            reason=REASON_RATE_LIMITED,
        )
        if rate is not None:
            return rate
        token = f"sub_{uuid4().hex[:12]}"
        self._submits[token] = ACTION_SUBMIT
        self._in_flight[token] = ACTION_SUBMIT
        return Admission(True, token=token)

    def _admit_recovery_unlocked(self, activity_id: str) -> Admission:
        if (
            self.limits.max_recovery_polls_per_activity <= 0
            or self.limits.max_recovery_polls_per_window <= 0
        ):
            return Admission(False, REASON_CLOSED)
        used = self._polls_by_activity.get(activity_id, 0)
        if used >= self.limits.max_recovery_polls_per_activity:
            return Admission(False, REASON_RECOVERY_POLL_CAP)
        rate = self._take_rate(
            self._recovery_hits,
            max_events=self.limits.max_recovery_polls_per_window,
            reason=REASON_RECOVERY_POLL_CAP,
        )
        if rate is not None:
            return rate
        self._polls_by_activity[activity_id] = used + 1
        return Admission(True, token=f"pol_{uuid4().hex[:12]}")

    def _queue_or_reject(
        self,
        kind: OpKind,
        queue_on_full: bool,
        cap_reason: str = REASON_RESERVE_CAP,
    ) -> Admission:
        if not queue_on_full or self.limits.queue_depth <= 0:
            return Admission(False, cap_reason)
        if len(self._queue) >= self.limits.queue_depth:
            return Admission(False, REASON_BACKPRESSURE)
        token = f"q_{uuid4().hex[:12]}"
        self._queue.append(QueuedWork(kind, token, self._now()))
        return Admission(False, REASON_QUEUED, token=token, queued=True)

    def _take_rate(
        self,
        bucket: deque[float],
        *,
        max_events: int,
        reason: str,
    ) -> Admission | None:
        now = self._now()
        cutoff = now - self.limits.window_seconds
        while bucket and bucket[0] <= cutoff:
            bucket.popleft()
        if len(bucket) >= max_events:
            oldest = bucket[0]
            retry = max(1, int(self.limits.window_seconds - (now - oldest) + 0.999))
            return Admission(
                False,
                reason,
                retry_after_seconds=retry,
            )
        bucket.append(now)
        return None


_DEFAULT_GUARDS: LiveResourceGuards | None = None
_DEFAULT_LOCK = Lock()


def get_live_resource_guards() -> LiveResourceGuards:
    """Process singleton. Tests should construct their own instance."""
    global _DEFAULT_GUARDS
    with _DEFAULT_LOCK:
        if _DEFAULT_GUARDS is None:
            _DEFAULT_GUARDS = LiveResourceGuards(limits_from_operator_env())
        return _DEFAULT_GUARDS


def reset_live_resource_guards() -> None:
    global _DEFAULT_GUARDS
    with _DEFAULT_LOCK:
        _DEFAULT_GUARDS = None


def hosted_live_stays_off_here() -> bool:
    """This module cannot turn hosted live on."""
    return True
