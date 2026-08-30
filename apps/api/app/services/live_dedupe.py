"""LIVE-G live-submit join: fingerprint → cache/join → one reserve+submit.

Dedupe happens before any allowance reservation. Joiners never spend and
never call the vendor. The vendor is assumed to lack idempotency.

This coordinator is J0 process-local. It is not a second job system: the
leader persists an AnalysisJob on the existing JobStore.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from threading import Event, Lock, RLock
from typing import Any, Callable, Protocol
from uuid import uuid4

from app.core.job_store import AnalysisJob, InMemoryJobStore, JobStore
from app.domain.demo_allowance import (
    DemoAllowanceDecision,
    DemoAllowanceDecisionCode,
    DemoRequestIdentity,
)
from app.domain.enums import JobStatus
from app.domain.live_dedupe import (
    AT_MOST_ONE_SUBMIT,
    LIVE_SUBMIT_FINGERPRINT_EXCLUDED,
    LIVE_SUBMIT_FINGERPRINT_VERSION,
    AtMostOneSubmitContract,
    LiveAcquireRequest,
    LiveAcquireResult,
    LiveJoinOutcome,
    LiveJoinPhase,
)
from app.domain.signals import ThermalSignalKind
from app.services.demo_allowance_ledger import InMemoryDemoAllowanceLedger
from app.services.snapshot_identity import (
    snapshot_request_document,
    snapshot_request_fingerprint,
)


OnCacheMiss = Callable[[str], None]


class LiveResultCache(Protocol):
    def get(self, fingerprint: str) -> dict[str, Any] | None: ...

    def put(self, fingerprint: str, result: dict[str, Any]) -> None: ...


class LiveVendorPort(Protocol):
    """Mockable vendor. LIVE-G never imports FortyGuard."""

    def submit(self, fingerprint: str, request: LiveAcquireRequest) -> str: ...

    def fetch(self, activity_id: str) -> dict[str, Any]: ...


class LiveAllowancePort(Protocol):
    def try_reserve(
        self, identity: DemoRequestIdentity, *, planned_units: int
    ) -> DemoAllowanceDecision: ...

    def consume(self, reservation_id: str, identity: DemoRequestIdentity, *, planned_units: int) -> None: ...

    def release(self, reservation_id: str) -> None: ...


class InMemoryLiveResultCache:
    def __init__(self) -> None:
        self._hits: dict[str, dict[str, Any]] = {}
        self._lock = Lock()

    def get(self, fingerprint: str) -> dict[str, Any] | None:
        with self._lock:
            hit = self._hits.get(fingerprint)
            return None if hit is None else dict(hit)

    def put(self, fingerprint: str, result: dict[str, Any]) -> None:
        with self._lock:
            self._hits[fingerprint] = dict(result)


class CountingMockVendor:
    """In-process vendor stand-in. Counts submits. No network."""

    def __init__(self, *, fail_submit: bool = False) -> None:
        self._lock = Lock()
        self.submit_count = 0
        self.fetch_count = 0
        self.fail_submit = fail_submit
        self.submitted_fingerprints: list[str] = []
        self._activities: dict[str, dict[str, Any]] = {}

    def submit(self, fingerprint: str, request: LiveAcquireRequest) -> str:
        with self._lock:
            self.submit_count += 1
            self.submitted_fingerprints.append(fingerprint)
            if self.fail_submit:
                raise RuntimeError("mock_vendor_submit_failed")
            activity_id = f"act_{uuid4().hex[:12]}"
            self._activities[activity_id] = {
                "fingerprint": fingerprint,
                "area_id": request.area_id,
                "target_timestamp": request.target_timestamp.isoformat(),
                "activity_id": activity_id,
            }
            return activity_id

    def fetch(self, activity_id: str) -> dict[str, Any]:
        with self._lock:
            self.fetch_count += 1
            payload = self._activities.get(activity_id)
            if payload is None:
                raise RuntimeError("unknown_activity")
            return {
                "ok": True,
                "activity_id": activity_id,
                "fingerprint": payload["fingerprint"],
                "area_id": payload["area_id"],
                "target_timestamp": payload["target_timestamp"],
            }


class CountingAllowance:
    """Wraps the demo ledger and counts reserve attempts that reach the ledger."""

    def __init__(self, ledger: InMemoryDemoAllowanceLedger) -> None:
        self._ledger = ledger
        self._lock = Lock()
        self.reserve_calls = 0
        self.consume_calls = 0
        self.release_calls = 0

    def try_reserve(
        self, identity: DemoRequestIdentity, *, planned_units: int
    ) -> DemoAllowanceDecision:
        with self._lock:
            self.reserve_calls += 1
        return self._ledger.try_reserve(identity, planned_units=planned_units)

    def consume(
        self,
        reservation_id: str,
        identity: DemoRequestIdentity,
        *,
        planned_units: int,
    ) -> None:
        with self._lock:
            self.consume_calls += 1
        self._ledger.consume(
            reservation_id, identity=identity, planned_units=planned_units
        )

    def release(self, reservation_id: str) -> None:
        with self._lock:
            self.release_calls += 1
        self._ledger.release(reservation_id)


def live_submit_fingerprint(request: LiveAcquireRequest) -> str:
    """Vendor-submit / cache / join key. Identical to snapshot_request_fingerprint."""
    return snapshot_request_fingerprint(
        area_id=request.area_id,
        geometry_sha256=request.geometry_sha256,
        zone_geometry_version=request.zone_geometry_version,
        target_timestamp=request.target_timestamp,
        timezone=request.timezone,
        analytic=request.analytic,
        granularity_m=request.granularity_m,
        aggregation_spec_version=request.aggregation_spec_version,
        temporal_mode=request.temporal_mode,
        adapter_version=request.adapter_version,
    )


def live_submit_document(request: LiveAcquireRequest) -> dict[str, Any]:
    doc = snapshot_request_document(
        area_id=request.area_id,
        geometry_sha256=request.geometry_sha256,
        zone_geometry_version=request.zone_geometry_version,
        target_timestamp=request.target_timestamp,
        timezone=request.timezone,
        analytic=request.analytic,
        granularity_m=request.granularity_m,
        aggregation_spec_version=request.aggregation_spec_version,
        temporal_mode=request.temporal_mode,
        adapter_version=request.adapter_version,
    )
    assert doc["identity_version"] == LIVE_SUBMIT_FINGERPRINT_VERSION
    return doc


def fingerprint_excludes_client_and_spend_fields(document: dict[str, Any]) -> bool:
    lowered = {key.lower() for key in document}
    for excluded in LIVE_SUBMIT_FINGERPRINT_EXCLUDED:
        if excluded.lower() in lowered:
            return False
        if excluded.lower() in " ".join(str(v).lower() for v in document.values()):
            # Values may legitimately contain substrings; only reject known keys.
            continue
    return "reference" not in " ".join(document.keys()).lower()


def _identity(request: LiveAcquireRequest, fingerprint: str) -> DemoRequestIdentity:
    return DemoRequestIdentity(
        signal_kind=ThermalSignalKind.SELECTED_TIME_SNAPSHOT,
        request_fingerprint=fingerprint,
        geometry_sha256=request.geometry_sha256,
        area_id=request.area_id,
        analytic=request.analytic,
        granularity_m=request.granularity_m,
        temporal_mode=request.temporal_mode,
    )


_IN_FLIGHT = frozenset(
    {
        LiveJoinPhase.OPEN,
        LiveJoinPhase.ALLOWANCE_RESERVED,
        LiveJoinPhase.SUBMITTING,
        LiveJoinPhase.SUBMITTED,
        LiveJoinPhase.ACTIVITY_ID_PERSISTED,
    }
)
_NO_RESUBMIT = frozenset(
    {
        LiveJoinPhase.FAILED_POST_SUBMIT,
        LiveJoinPhase.UNKNOWN_VENDOR_STATE,
        LiveJoinPhase.SUCCEEDED,
    }
)


@dataclass
class _JoinRecord:
    fingerprint: str
    job_id: str
    phase: LiveJoinPhase = LiveJoinPhase.OPEN
    submit_slot_taken: bool = False
    reservation_id: str | None = None
    activity_id: str | None = None
    result: dict[str, Any] | None = None
    error: str | None = None
    joiner_count: int = 0
    done: Event = field(default_factory=Event)


class LiveDedupeCoordinator:
    """Cache/join before spend. One leader per fingerprint may reserve+submit."""

    def __init__(
        self,
        *,
        store: JobStore | None = None,
        cache: LiveResultCache | None = None,
        allowance: LiveAllowancePort | None = None,
        vendor: LiveVendorPort | None = None,
    ) -> None:
        self._store = store or InMemoryJobStore()
        self._cache = cache if cache is not None else InMemoryLiveResultCache()
        if allowance is None:
            raise ValueError("allowance port is required; coordinator will not invent spend")
        self._allowance = allowance
        self._vendor = vendor if vendor is not None else CountingMockVendor()
        self._lock = RLock()
        self._records: dict[str, _JoinRecord] = {}

    @property
    def store(self) -> JobStore:
        return self._store

    @property
    def vendor(self) -> LiveVendorPort:
        return self._vendor

    @property
    def allowance(self) -> LiveAllowancePort:
        return self._allowance

    @property
    def cache(self) -> LiveResultCache:
        return self._cache

    def execute(
        self,
        request: LiveAcquireRequest,
        *,
        on_cache_miss: OnCacheMiss | None = None,
        on_after_claim: Callable[[LiveAcquireResult], None] | None = None,
        allow_reopen: bool = False,
        join_timeout_s: float = 30.0,
    ) -> LiveAcquireResult:
        fingerprint = live_submit_fingerprint(request)
        cached = self._cache.get(fingerprint)
        if cached is None and on_cache_miss is not None:
            on_cache_miss(fingerprint)

        ticket = self._claim(request, fingerprint, allow_reopen=allow_reopen)
        if on_after_claim is not None:
            on_after_claim(ticket)
        if ticket.outcome == LiveJoinOutcome.CACHE_HIT:
            return ticket
        if ticket.outcome == LiveJoinOutcome.JOINED:
            return self._await_leader(ticket, join_timeout_s=join_timeout_s)
        if ticket.outcome == LiveJoinOutcome.RECOVERY_REQUIRED:
            return ticket
        return self._lead(request, fingerprint, ticket.job_id)

    def _claim(
        self,
        request: LiveAcquireRequest,
        fingerprint: str,
        *,
        allow_reopen: bool,
    ) -> LiveAcquireResult:
        with self._lock:
            cached = self._cache.get(fingerprint)
            if cached is not None:
                existing = self._records.get(fingerprint)
                job_id = existing.job_id if existing is not None else f"cached_{fingerprint[:12]}"
                return LiveAcquireResult(
                    outcome=LiveJoinOutcome.CACHE_HIT,
                    fingerprint=fingerprint,
                    job_id=job_id,
                    phase=LiveJoinPhase.SUCCEEDED,
                    shared_result=dict(cached),
                )
            record = self._records.get(fingerprint)
            if record is None or (
                allow_reopen
                and record.phase == LiveJoinPhase.FAILED_PRE_SUBMIT
                and record.done.is_set()
            ):
                job = self._create_leader_job(request, fingerprint)
                record = _JoinRecord(fingerprint=fingerprint, job_id=job.job_id)
                self._records[fingerprint] = record
                return LiveAcquireResult(
                    outcome=LiveJoinOutcome.LEADER,
                    fingerprint=fingerprint,
                    job_id=job.job_id,
                    phase=LiveJoinPhase.OPEN,
                )
            if record.phase == LiveJoinPhase.FAILED_PRE_SUBMIT:
                record.joiner_count += 1
                return LiveAcquireResult(
                    outcome=LiveJoinOutcome.JOINED,
                    fingerprint=fingerprint,
                    job_id=record.job_id,
                    phase=record.phase,
                    error=record.error,
                    shared_result=None if record.result is None else dict(record.result),
                )
            if record.phase in _NO_RESUBMIT and record.phase != LiveJoinPhase.SUCCEEDED:
                record.joiner_count += 1
                return LiveAcquireResult(
                    outcome=LiveJoinOutcome.RECOVERY_REQUIRED,
                    fingerprint=fingerprint,
                    job_id=record.job_id,
                    phase=record.phase,
                    activity_id=record.activity_id,
                    error=record.error or "unknown_vendor_state_no_resubmit",
                    shared_result=record.result,
                )
            if record.phase == LiveJoinPhase.SUCCEEDED:
                return LiveAcquireResult(
                    outcome=LiveJoinOutcome.CACHE_HIT,
                    fingerprint=fingerprint,
                    job_id=record.job_id,
                    phase=LiveJoinPhase.SUCCEEDED,
                    shared_result=None if record.result is None else dict(record.result),
                )
            if record.phase in _IN_FLIGHT:
                record.joiner_count += 1
                return LiveAcquireResult(
                    outcome=LiveJoinOutcome.JOINED,
                    fingerprint=fingerprint,
                    job_id=record.job_id,
                    phase=LiveJoinPhase.OPEN,
                )
            record.joiner_count += 1
            return LiveAcquireResult(
                outcome=LiveJoinOutcome.JOINED,
                fingerprint=fingerprint,
                job_id=record.job_id,
                phase=record.phase,
            )

    def _create_leader_job(
        self, request: LiveAcquireRequest, fingerprint: str
    ) -> AnalysisJob:
        payload = {
            "area_id": request.area_id,
            "target_timestamp": request.target_timestamp.isoformat(),
            "live_join_fingerprint": fingerprint,
        }
        existing = self._store.find_by_dedupe_key(fingerprint)
        if existing is not None and existing.status not in {
            JobStatus.FAILED,
            JobStatus.COMPLETE,
            JobStatus.PARTIAL,
        }:
            return existing
        if existing is not None and existing.status in {
            JobStatus.COMPLETE,
            JobStatus.PARTIAL,
        }:
            return existing
        job, _joined = self._store.create_or_join(payload, dedupe_key=fingerprint)
        return job

    def _await_leader(
        self, ticket: LiveAcquireResult, *, join_timeout_s: float
    ) -> LiveAcquireResult:
        record = self._records[ticket.fingerprint]
        finished = record.done.wait(timeout=join_timeout_s)
        if not finished:
            return ticket.model_copy(
                update={"error": "join_wait_timeout", "phase": record.phase}
            )
        if record.phase in {
            LiveJoinPhase.FAILED_POST_SUBMIT,
            LiveJoinPhase.UNKNOWN_VENDOR_STATE,
        }:
            outcome = LiveJoinOutcome.RECOVERY_REQUIRED
        elif record.phase == LiveJoinPhase.FAILED_PRE_SUBMIT:
            outcome = LiveJoinOutcome.JOINED
        else:
            outcome = LiveJoinOutcome.JOINED
        return LiveAcquireResult(
            outcome=outcome,
            fingerprint=ticket.fingerprint,
            job_id=record.job_id,
            phase=record.phase,
            shared_result=None if record.result is None else dict(record.result),
            reservation_id=record.reservation_id,
            activity_id=record.activity_id,
            error=record.error,
            submitted=False,
            reserved=False,
        )

    def _lead(
        self, request: LiveAcquireRequest, fingerprint: str, job_id: str
    ) -> LiveAcquireResult:
        record = self._records[fingerprint]
        identity = _identity(request, fingerprint)
        reserved = False
        reservation_id: str | None = None
        submitted = False
        try:
            decision = self._allowance.try_reserve(
                identity, planned_units=request.planned_units
            )
            if (
                decision.code != DemoAllowanceDecisionCode.ELIGIBLE
                or decision.reservation is None
                or not decision.spend_authorized
            ):
                if decision.code == DemoAllowanceDecisionCode.JOIN_EXISTING_RESERVATION:
                    # Another reservation exists; this coordinator still must not
                    # submit. Joiners of *this* record wait on the published error.
                    self._finish_pre_submit(
                        record,
                        error=f"allowance_{decision.code.value}",
                    )
                    return LiveAcquireResult(
                        outcome=LiveJoinOutcome.LEADER,
                        fingerprint=fingerprint,
                        job_id=job_id,
                        phase=LiveJoinPhase.FAILED_PRE_SUBMIT,
                        error=f"allowance_{decision.code.value}",
                        reserved=False,
                    )
                self._finish_pre_submit(
                    record, error=f"allowance_{decision.code.value}"
                )
                return LiveAcquireResult(
                    outcome=LiveJoinOutcome.LEADER,
                    fingerprint=fingerprint,
                    job_id=job_id,
                    phase=LiveJoinPhase.FAILED_PRE_SUBMIT,
                    error=f"allowance_{decision.code.value}",
                    reserved=False,
                )
            reservation_id = decision.reservation.reservation_id
            reserved = True
            with self._lock:
                record.reservation_id = reservation_id
                record.phase = LiveJoinPhase.ALLOWANCE_RESERVED
                if record.submit_slot_taken:
                    self._finish_pre_submit(record, error="submit_slot_already_taken")
                    self._allowance.release(reservation_id)
                    return LiveAcquireResult(
                        outcome=LiveJoinOutcome.LEADER,
                        fingerprint=fingerprint,
                        job_id=job_id,
                        phase=LiveJoinPhase.FAILED_PRE_SUBMIT,
                        error="submit_slot_already_taken",
                        reserved=True,
                        reservation_id=reservation_id,
                    )
                # Irreversible for this attempt: taken BEFORE vendor I/O.
                assert AT_MOST_ONE_SUBMIT.submit_slot_taken_before_vendor_io
                record.submit_slot_taken = True
                record.phase = LiveJoinPhase.SUBMITTING

            try:
                activity_id = self._vendor.submit(fingerprint, request)
            except Exception as exc:
                submitted = True
                with self._lock:
                    record.phase = LiveJoinPhase.UNKNOWN_VENDOR_STATE
                    record.error = f"submit_uncertain:{exc}"
                self._store.mark_interrupted(
                    job_id, message="submit_uncertain_no_resubmit"
                )
                return LiveAcquireResult(
                    outcome=LiveJoinOutcome.RECOVERY_REQUIRED,
                    fingerprint=fingerprint,
                    job_id=job_id,
                    phase=LiveJoinPhase.UNKNOWN_VENDOR_STATE,
                    reservation_id=reservation_id,
                    error=record.error,
                    submitted=True,
                    reserved=True,
                )

            submitted = True
            with self._lock:
                record.activity_id = activity_id
                record.phase = LiveJoinPhase.ACTIVITY_ID_PERSISTED

            fetched = self._vendor.fetch(activity_id)
            shared = {
                **fetched,
                "job_id": job_id,
                "fingerprint": fingerprint,
            }
            self._cache.put(fingerprint, shared)
            self._allowance.consume(
                reservation_id, identity, planned_units=request.planned_units
            )
            with self._lock:
                record.result = shared
                record.phase = LiveJoinPhase.SUCCEEDED
            self._store.set_result(job_id, shared, JobStatus.COMPLETE)
            return LiveAcquireResult(
                outcome=LiveJoinOutcome.LEADER,
                fingerprint=fingerprint,
                job_id=job_id,
                phase=LiveJoinPhase.SUCCEEDED,
                shared_result=shared,
                reservation_id=reservation_id,
                activity_id=activity_id,
                submitted=True,
                reserved=True,
            )
        except Exception as exc:
            if submitted:
                with self._lock:
                    record.phase = LiveJoinPhase.FAILED_POST_SUBMIT
                    record.error = str(exc)
                return LiveAcquireResult(
                    outcome=LiveJoinOutcome.RECOVERY_REQUIRED,
                    fingerprint=fingerprint,
                    job_id=job_id,
                    phase=LiveJoinPhase.FAILED_POST_SUBMIT,
                    reservation_id=reservation_id,
                    activity_id=record.activity_id,
                    error=str(exc),
                    submitted=True,
                    reserved=reserved,
                )
            if reserved and reservation_id is not None:
                try:
                    self._allowance.release(reservation_id)
                except Exception:
                    pass
            self._finish_pre_submit(record, error=str(exc))
            return LiveAcquireResult(
                outcome=LiveJoinOutcome.LEADER,
                fingerprint=fingerprint,
                job_id=job_id,
                phase=LiveJoinPhase.FAILED_PRE_SUBMIT,
                error=str(exc),
                reserved=reserved,
                reservation_id=reservation_id,
            )
        finally:
            record.done.set()

    def _finish_pre_submit(self, record: _JoinRecord, *, error: str) -> None:
        with self._lock:
            if record.phase in _NO_RESUBMIT and record.phase != LiveJoinPhase.SUCCEEDED:
                return
            if record.phase in {
                LiveJoinPhase.SUBMITTING,
                LiveJoinPhase.SUBMITTED,
                LiveJoinPhase.ACTIVITY_ID_PERSISTED,
                LiveJoinPhase.UNKNOWN_VENDOR_STATE,
                LiveJoinPhase.FAILED_POST_SUBMIT,
            }:
                return
            record.phase = LiveJoinPhase.FAILED_PRE_SUBMIT
            record.error = error
        self._store.update_status(
            record.job_id, JobStatus.FAILED, message=error
        )


def at_most_one_submit_contract() -> AtMostOneSubmitContract:
    return AT_MOST_ONE_SUBMIT
