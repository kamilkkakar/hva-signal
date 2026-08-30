"""Cache recheck guards for hosted live spend. No FortyGuard. No real vendor.

Order is mandatory:
  recheck BEFORE_RESERVE → (optional) reserve → recheck BEFORE_SUBMIT
  → submit at most once → result → normalize → cache → consume.

CACHE_HIT never reserves and never submits. Recovery after a result never
resubmits. Client cache-bust and client cache writes are rejected.
"""

from __future__ import annotations

import hashlib
import json
from datetime import datetime, timezone
from threading import Lock
from typing import Any, Mapping
from uuid import uuid4

from app.core.job_store import JobStore
from app.domain.demo_allowance import (
    DemoAllowanceDecision,
    DemoAllowanceDecisionCode,
    DemoRequestIdentity,
    ReservationState,
)
from app.domain.enums import JobStatus
from app.domain.live_cache_recheck import (
    CACHE_RECHECK_CONTRACT_VERSION,
    CacheRecheckCode,
    CacheRecheckDecision,
    CacheRecheckError,
    CrashAfter,
    FingerprintCacheRecord,
    LiveCacheJob,
    LiveCachePhase,
    NormalizedLiveResult,
    RecheckPoint,
)
from app.services.demo_allowance_ledger import (
    DemoAllowanceError,
    InMemoryDemoAllowanceLedger,
)
from app.services.secret_boundary import public_payload_leaks_secrets

_TERMINAL_OK = frozenset({JobStatus.COMPLETE, JobStatus.PARTIAL})

CLIENT_CACHE_BUST_KEYS = frozenset(
    {
        "bypass_cache",
        "bust_cache",
        "cache_bust",
        "cache_skip",
        "force_live",
        "force_refresh",
        "no_cache",
        "nocache",
        "purge_cache",
        "refresh_cache",
        "skip_cache",
    }
)

_CLIENT_CACHE_WRITE_KEYS = frozenset(
    {
        "cache_payload",
        "cache_record",
        "cached_result",
        "inject_cache",
        "seed_cache",
    }
)

_SECRET_STRIP_KEYS = frozenset(
    {
        "allowance_remaining",
        "api_key",
        "apikey",
        "authorization",
        "demo_budget",
        "fortyguard_api_key",
        "internal_key",
        "password",
        "secret",
        "x-api-key",
        "x_api_key",
    }
)

_HEADER_ALIASES = {
    "x-cache-bust": "cache_bust",
    "x-no-cache": "no_cache",
    "x-force-live": "force_live",
    "cache-control": "cache_control",
}


class SimulatedCrash(RuntimeError):
    """Test-only crash after a committed phase. Recovery must not resubmit."""

    def __init__(self, phase: LiveCachePhase) -> None:
        super().__init__(f"simulated_crash_after_{phase.value}")
        self.phase = phase


def _now() -> datetime:
    return datetime.now(timezone.utc)


def _canonical_json(value: Any) -> str:
    return json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=True)


def _lower_keys(mapping: Mapping[str, Any] | None) -> dict[str, Any]:
    if not mapping:
        return {}
    return {str(key).lower(): value for key, value in mapping.items()}


def client_cache_bust_keys(
    payload: Mapping[str, Any] | None = None,
    *,
    headers: Mapping[str, Any] | None = None,
    query: Mapping[str, Any] | None = None,
) -> list[str]:
    """Names a client used to request a cache bypass. Presence is enough."""

    found: set[str] = set()
    for source in (payload, query):
        if not source:
            continue
        for key in source:
            lowered = str(key).lower()
            if lowered in CLIENT_CACHE_BUST_KEYS:
                found.add(lowered)
    headers_l = _lower_keys(headers)
    for header, alias in _HEADER_ALIASES.items():
        if header not in headers_l:
            continue
        if alias in CLIENT_CACHE_BUST_KEYS:
            found.add(alias)
        raw = headers_l[header]
        if header == "cache-control" and isinstance(raw, str):
            tokens = {part.strip().lower() for part in raw.split(",")}
            if tokens & {"no-cache", "no-store", "max-age=0"}:
                found.add("no_cache")
    return sorted(found)


def client_cache_write_keys(payload: Mapping[str, Any] | None) -> list[str]:
    if not payload:
        return []
    return sorted(key for key in payload if str(key).lower() in _CLIENT_CACHE_WRITE_KEYS)


def reject_unauthenticated_cache_control(
    payload: Mapping[str, Any] | None = None,
    *,
    headers: Mapping[str, Any] | None = None,
    query: Mapping[str, Any] | None = None,
) -> None:
    """Client cache-bust and client cache writes are never honored."""

    bust = client_cache_bust_keys(payload, headers=headers, query=query)
    if bust:
        raise CacheRecheckError(
            CacheRecheckCode.REJECTED_CACHE_BUST,
            f"unauthenticated cache-bust rejected: {','.join(bust)}",
        )
    writes = client_cache_write_keys(payload)
    if writes:
        raise CacheRecheckError(
            CacheRecheckCode.REJECTED_POISON,
            f"client cache write rejected: {','.join(writes)}",
        )
    if payload:
        for key in payload:
            if str(key).lower() in {"operator_token", "operator_cache_bust", "cache_operator"}:
                raise CacheRecheckError(
                    CacheRecheckCode.REJECTED_UNAUTHENTICATED,
                    "operator cache-bust cannot arrive on a client payload",
                )


def strip_secrets(value: Any) -> Any:
    if isinstance(value, dict):
        out: dict[str, Any] = {}
        for key, inner in value.items():
            lowered = str(key).lower()
            if lowered in _SECRET_STRIP_KEYS or "api_key" in lowered:
                continue
            out[str(key)] = strip_secrets(inner)
        return out
    if isinstance(value, list):
        return [strip_secrets(item) for item in value]
    return value


def compute_integrity(
    *,
    request_fingerprint: str,
    geometry_sha256: str,
    area_id: str,
    payload: dict[str, Any],
) -> str:
    document = {
        "area_id": area_id,
        "contract_version": CACHE_RECHECK_CONTRACT_VERSION,
        "geometry_sha256": geometry_sha256,
        "payload": payload,
        "request_fingerprint": request_fingerprint,
    }
    return hashlib.sha256(_canonical_json(document).encode("utf-8")).hexdigest()


def normalize_live_result(
    identity: DemoRequestIdentity,
    raw_result: dict[str, Any],
) -> NormalizedLiveResult:
    """Bind the vendor-neutral result to the request identity. No AOI min-max."""

    if not isinstance(raw_result, dict):
        raise CacheRecheckError(
            CacheRecheckCode.REJECTED_POISON,
            "raw result must be an object",
        )
    frame = raw_result.get("reference_frame")
    if isinstance(frame, str) and frame.lower() == "relative":
        raise CacheRecheckError(
            CacheRecheckCode.REJECTED_POISON,
            "RELATIVE / AOI min-max cannot be cached as a live result",
        )
    planted = raw_result.get("request_fingerprint")
    if planted is not None and planted != identity.request_fingerprint:
        raise CacheRecheckError(
            CacheRecheckCode.REJECTED_IDENTITY,
            "result fingerprint does not match request identity",
        )
    planted_geo = raw_result.get("geometry_sha256")
    if planted_geo is not None and planted_geo != identity.geometry_sha256:
        raise CacheRecheckError(
            CacheRecheckCode.REJECTED_IDENTITY,
            "result geometry does not match request identity",
        )
    payload = strip_secrets(raw_result)
    if public_payload_leaks_secrets(payload):
        payload = strip_secrets(payload)
    integrity = compute_integrity(
        request_fingerprint=identity.request_fingerprint,
        geometry_sha256=identity.geometry_sha256,
        area_id=identity.area_id,
        payload=payload,
    )
    return NormalizedLiveResult(
        request_fingerprint=identity.request_fingerprint,
        geometry_sha256=identity.geometry_sha256,
        area_id=identity.area_id,
        payload=payload,
        integrity_sha256=integrity,
    )


def record_integrity_holds(record: FingerprintCacheRecord) -> bool:
    expected = compute_integrity(
        request_fingerprint=record.request_fingerprint,
        geometry_sha256=record.geometry_sha256,
        area_id=record.area_id,
        payload=record.payload,
    )
    return expected == record.integrity_sha256


class FingerprintResultCache:
    """Process-local identity-bound result cache. Worker writes only."""

    def __init__(self) -> None:
        self._lock = Lock()
        self._records: dict[str, FingerprintCacheRecord] = {}

    def get(self, identity: DemoRequestIdentity) -> FingerprintCacheRecord | None:
        with self._lock:
            record = self._records.get(identity.request_fingerprint)
            if record is None:
                return None
            if (
                record.geometry_sha256 != identity.geometry_sha256
                or record.area_id != identity.area_id
            ):
                return None
            if not record_integrity_holds(record):
                del self._records[identity.request_fingerprint]
                return None
            return record

    def put_from_worker(
        self,
        identity: DemoRequestIdentity,
        normalized: NormalizedLiveResult,
        *,
        now: datetime | None = None,
    ) -> FingerprintCacheRecord:
        if normalized.request_fingerprint != identity.request_fingerprint:
            raise CacheRecheckError(
                CacheRecheckCode.REJECTED_IDENTITY,
                "cannot cache a result for a different fingerprint",
            )
        if normalized.geometry_sha256 != identity.geometry_sha256:
            raise CacheRecheckError(
                CacheRecheckCode.REJECTED_IDENTITY,
                "cannot cache a result for a different geometry",
            )
        if normalized.area_id != identity.area_id:
            raise CacheRecheckError(
                CacheRecheckCode.REJECTED_IDENTITY,
                "cannot cache a result for a different area",
            )
        expected = compute_integrity(
            request_fingerprint=identity.request_fingerprint,
            geometry_sha256=identity.geometry_sha256,
            area_id=identity.area_id,
            payload=normalized.payload,
        )
        if expected != normalized.integrity_sha256:
            raise CacheRecheckError(
                CacheRecheckCode.REJECTED_INTEGRITY,
                "normalized integrity does not match payload",
            )
        record = FingerprintCacheRecord(
            request_fingerprint=identity.request_fingerprint,
            geometry_sha256=identity.geometry_sha256,
            area_id=identity.area_id,
            payload=normalized.payload,
            integrity_sha256=expected,
            cached_at=now or _now(),
            writer="worker",
        )
        with self._lock:
            existing = self._records.get(identity.request_fingerprint)
            if existing is not None and existing.integrity_sha256 != record.integrity_sha256:
                raise CacheRecheckError(
                    CacheRecheckCode.REJECTED_POISON,
                    "refusing to overwrite a cached result with a different payload",
                )
            self._records[identity.request_fingerprint] = record
            return record

    def ingest_client_record(
        self,
        identity: DemoRequestIdentity,
        record: Mapping[str, Any],
    ) -> None:
        del identity, record
        raise CacheRecheckError(
            CacheRecheckCode.REJECTED_POISON,
            "unauthenticated cache ingest is rejected",
        )

    def operator_bust(
        self,
        *,
        request_fingerprint: str,
        operator_token: str,
        configured_token: str,
        source: str,
    ) -> None:
        if source != "server":
            raise CacheRecheckError(
                CacheRecheckCode.REJECTED_UNAUTHENTICATED,
                "cache-bust source is not server-side",
            )
        if not configured_token or operator_token != configured_token:
            raise CacheRecheckError(
                CacheRecheckCode.REJECTED_UNAUTHENTICATED,
                "operator cache-bust token rejected",
            )
        with self._lock:
            self._records.pop(request_fingerprint, None)


def _job_store_reusable(store: JobStore | None, dedupe_key: str | None) -> str | None:
    if store is None or not dedupe_key:
        return None
    existing = store.find_by_dedupe_key(dedupe_key)
    if existing is not None and existing.status in _TERMINAL_OK:
        return existing.job_id
    return None


def recheck_cache(
    *,
    cache: FingerprintResultCache,
    identity: DemoRequestIdentity,
    point: RecheckPoint,
    store: JobStore | None = None,
    dedupe_key: str | None = None,
) -> CacheRecheckDecision:
    """Immediate cache lookup. Either fingerprint or reusable job is a hit."""

    job_id = _job_store_reusable(store, dedupe_key)
    record = cache.get(identity)
    if record is not None or job_id is not None:
        return CacheRecheckDecision(
            code=CacheRecheckCode.CACHE_HIT,
            point=point,
            record=record,
            joined_job_id=job_id,
            reserve_allowed=False,
            submit_allowed=False,
        )
    return CacheRecheckDecision(
        code=CacheRecheckCode.CACHE_MISS,
        point=point,
        reserve_allowed=point == RecheckPoint.BEFORE_RESERVE,
        submit_allowed=point == RecheckPoint.BEFORE_SUBMIT,
    )


def gate_reserve(
    *,
    cache: FingerprintResultCache,
    ledger: InMemoryDemoAllowanceLedger,
    identity: DemoRequestIdentity,
    planned_units: int,
    now: datetime | None = None,
    store: JobStore | None = None,
    dedupe_key: str | None = None,
) -> tuple[CacheRecheckDecision, DemoAllowanceDecision | None]:
    """Recheck immediately before reserve. CACHE_HIT does not touch the ledger."""

    decision = recheck_cache(
        cache=cache,
        identity=identity,
        point=RecheckPoint.BEFORE_RESERVE,
        store=store,
        dedupe_key=dedupe_key,
    )
    if decision.code == CacheRecheckCode.CACHE_HIT:
        return decision, None
    reserved = ledger.try_reserve(
        identity,
        planned_units=planned_units,
        now=now or _now(),
    )
    return decision, reserved


def gate_submit(
    *,
    cache: FingerprintResultCache,
    ledger: InMemoryDemoAllowanceLedger,
    identity: DemoRequestIdentity,
    reservation_id: str,
    store: JobStore | None = None,
    dedupe_key: str | None = None,
) -> CacheRecheckDecision:
    """Recheck immediately before submit. Hit releases the reservation. No consume."""

    decision = recheck_cache(
        cache=cache,
        identity=identity,
        point=RecheckPoint.BEFORE_SUBMIT,
        store=store,
        dedupe_key=dedupe_key,
    )
    if decision.code != CacheRecheckCode.CACHE_HIT:
        reservation = ledger.get(reservation_id)
        if reservation is None or reservation.state != ReservationState.RESERVED:
            return decision.model_copy(
                update={
                    "code": CacheRecheckCode.REJECTED_IDENTITY,
                    "submit_allowed": False,
                    "reserve_allowed": False,
                }
            )
        if reservation.request_fingerprint != identity.request_fingerprint:
            return decision.model_copy(
                update={
                    "code": CacheRecheckCode.REJECTED_IDENTITY,
                    "submit_allowed": False,
                    "reserve_allowed": False,
                }
            )
        return decision

    released: str | None = None
    reservation = ledger.get(reservation_id)
    if reservation is not None and reservation.state == ReservationState.RESERVED:
        ledger.release(reservation_id)
        released = reservation_id
    return decision.model_copy(update={"released_reservation_id": released})


def consume_after_cache(
    *,
    ledger: InMemoryDemoAllowanceLedger,
    reservation_id: str,
    identity: DemoRequestIdentity,
    planned_units: int,
    now: datetime | None = None,
) -> ReservationState:
    """Consume is legal only after a successful cache put. Idempotent if consumed."""

    reservation = ledger.get(reservation_id)
    if reservation is None:
        raise DemoAllowanceError("unknown_reservation")
    if reservation.state == ReservationState.CONSUMED:
        return ReservationState.CONSUMED
    ledger.consume(
        reservation_id,
        identity=identity,
        planned_units=planned_units,
        now=now or _now(),
    )
    return ReservationState.CONSUMED


class LiveCachePipeline:
    """Worker-side post-result path with crash injection. No vendor I/O."""

    def __init__(
        self,
        *,
        cache: FingerprintResultCache,
        ledger: InMemoryDemoAllowanceLedger,
        identity: DemoRequestIdentity,
        planned_units: int = 1,
    ) -> None:
        self.cache = cache
        self.ledger = ledger
        self.identity = identity
        self.planned_units = planned_units
        self.job = LiveCacheJob(
            job_id=f"liveh_{uuid4().hex[:12]}",
            phase=LiveCachePhase.VALIDATED,
            request_fingerprint=identity.request_fingerprint,
            geometry_sha256=identity.geometry_sha256,
            area_id=identity.area_id,
            planned_units=planned_units,
        )

    def reserve(self, *, now: datetime | None = None, store: JobStore | None = None, dedupe_key: str | None = None) -> CacheRecheckDecision:
        decision, reserved = gate_reserve(
            cache=self.cache,
            ledger=self.ledger,
            identity=self.identity,
            planned_units=self.planned_units,
            now=now,
            store=store,
            dedupe_key=dedupe_key,
        )
        if decision.code == CacheRecheckCode.CACHE_HIT:
            self.job = self.job.model_copy(update={"phase": LiveCachePhase.CACHE_HIT})
            return decision
        joined = reserved is not None and reserved.code in {
            DemoAllowanceDecisionCode.ELIGIBLE,
            DemoAllowanceDecisionCode.JOIN_EXISTING_RESERVATION,
        }
        if reserved is None or reserved.reservation is None or not joined:
            self.job = self.job.model_copy(
                update={
                    "phase": LiveCachePhase.FAILED_PRE_SUBMIT,
                    "last_error": None if reserved is None else reserved.code.value,
                }
            )
            return decision
        self.job = self.job.model_copy(
            update={
                "phase": LiveCachePhase.ALLOWANCE_RESERVED,
                "reservation_id": reserved.reservation.reservation_id,
            }
        )
        return decision

    def submit_if_allowed(self, *, store: JobStore | None = None, dedupe_key: str | None = None) -> CacheRecheckDecision:
        if self.job.phase == LiveCachePhase.CACHE_HIT:
            return CacheRecheckDecision(
                code=CacheRecheckCode.CACHE_HIT,
                point=RecheckPoint.BEFORE_SUBMIT,
            )
        if self.job.reservation_id is None:
            return CacheRecheckDecision(
                code=CacheRecheckCode.REJECTED_IDENTITY,
                point=RecheckPoint.BEFORE_SUBMIT,
            )
        decision = gate_submit(
            cache=self.cache,
            ledger=self.ledger,
            identity=self.identity,
            reservation_id=self.job.reservation_id,
            store=store,
            dedupe_key=dedupe_key,
        )
        if decision.code == CacheRecheckCode.CACHE_HIT:
            self.job = self.job.model_copy(
                update={
                    "phase": LiveCachePhase.CACHE_HIT,
                    "reservation_id": None
                    if decision.released_reservation_id
                    else self.job.reservation_id,
                }
            )
            return decision
        if not decision.submit_allowed:
            self.job = self.job.model_copy(
                update={"phase": LiveCachePhase.FAILED_PRE_SUBMIT}
            )
            return decision
        self.job = self.job.model_copy(
            update={
                "phase": LiveCachePhase.SUBMITTED,
                "submit_count": self.job.submit_count + 1,
            }
        )
        return decision

    def accept_result(
        self,
        raw_result: dict[str, Any],
        *,
        crash_after: CrashAfter | None = None,
        now: datetime | None = None,
    ) -> LiveCacheJob:
        """normalize → cache → consume. Crash leaves phase for recover()."""

        if self.job.submit_count < 1 and self.job.phase != LiveCachePhase.SUBMITTED:
            raise CacheRecheckError(
                CacheRecheckCode.REJECTED_IDENTITY,
                "cannot accept a result without a prior submit",
            )
        self.job = self.job.model_copy(
            update={
                "phase": LiveCachePhase.RESULT_RECEIVED,
                "raw_result": strip_secrets(raw_result),
                "recovery_required": False,
            }
        )
        if crash_after is CrashAfter.RESULT:
            self.job = self.job.model_copy(update={"recovery_required": True})
            raise SimulatedCrash(LiveCachePhase.RESULT_RECEIVED)
        return self._finish_from_result(crash_after=crash_after, now=now)

    def recover(self, *, now: datetime | None = None) -> LiveCacheJob:
        """Resume after crash. Never increments submit_count. Never resubmits."""

        if self.job.phase == LiveCachePhase.CONSUMED:
            return self.job
        if self.job.phase == LiveCachePhase.CACHED:
            return self._consume_only(now=now)
        if self.job.phase in {
            LiveCachePhase.RESULT_RECEIVED,
            LiveCachePhase.NORMALIZED,
            LiveCachePhase.RECOVERY_REQUIRED,
        }:
            if self.job.raw_result is None and self.job.normalized is None:
                self.job = self.job.model_copy(
                    update={
                        "phase": LiveCachePhase.RECOVERY_REQUIRED,
                        "last_error": "missing_result_for_cache_recovery",
                    }
                )
                return self.job
            return self._finish_from_result(crash_after=None, now=now)
        if self.job.phase in {
            LiveCachePhase.SUBMITTED,
            LiveCachePhase.SUBMITTING,
        }:
            self.job = self.job.model_copy(
                update={
                    "phase": LiveCachePhase.RECOVERY_REQUIRED,
                    "last_error": "unknown_vendor_state_no_resubmit",
                }
            )
            return self.job
        return self.job

    def _finish_from_result(
        self,
        *,
        crash_after: CrashAfter | None,
        now: datetime | None,
    ) -> LiveCacheJob:
        if self.job.normalized is None:
            assert self.job.raw_result is not None
            normalized = normalize_live_result(self.identity, self.job.raw_result)
            self.job = self.job.model_copy(
                update={"phase": LiveCachePhase.NORMALIZED, "normalized": normalized}
            )
        if crash_after is CrashAfter.NORMALIZE:
            self.job = self.job.model_copy(update={"recovery_required": True})
            raise SimulatedCrash(LiveCachePhase.NORMALIZED)
        assert self.job.normalized is not None
        record = self.cache.put_from_worker(
            self.identity,
            self.job.normalized,
            now=now,
        )
        self.job = self.job.model_copy(
            update={
                "phase": LiveCachePhase.CACHED,
                "cached_integrity": record.integrity_sha256,
                "recovery_required": False,
            }
        )
        if crash_after is CrashAfter.CACHE:
            self.job = self.job.model_copy(update={"recovery_required": True})
            raise SimulatedCrash(LiveCachePhase.CACHED)
        return self._consume_only(now=now)

    def _consume_only(self, *, now: datetime | None) -> LiveCacheJob:
        reservation_id = self.job.reservation_id
        if reservation_id is None:
            self.job = self.job.model_copy(
                update={
                    "phase": LiveCachePhase.CACHED,
                    "last_error": "cached_without_reservation",
                }
            )
            return self.job
        consume_after_cache(
            ledger=self.ledger,
            reservation_id=reservation_id,
            identity=self.identity,
            planned_units=self.planned_units,
            now=now,
        )
        self.job = self.job.model_copy(
            update={
                "phase": LiveCachePhase.CONSUMED,
                "consumed": True,
                "recovery_required": False,
            }
        )
        return self.job
