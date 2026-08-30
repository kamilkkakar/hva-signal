"""Ledger port shared by the process-local J0 ledger and the J3 SQLite store."""

from __future__ import annotations

from datetime import datetime
from typing import Protocol

from app.domain.demo_allowance import (
    AllowanceRestartReport,
    CachedDemoResult,
    ConsumeAfterCacheResult,
    DemoAllowanceDecision,
    DemoAllowancePolicy,
    DemoAllowanceState,
    DemoRequestIdentity,
    DemoReservation,
)


class DemoAllowanceLedgerPort(Protocol):
    durability: str

    @property
    def policy(self) -> DemoAllowancePolicy: ...

    def snapshot(self) -> DemoAllowanceState: ...

    def try_reserve(
        self,
        identity: DemoRequestIdentity,
        *,
        planned_units: int,
        now: datetime | None = None,
    ) -> DemoAllowanceDecision: ...

    def release(self, reservation_id: str) -> DemoReservation: ...

    def expire(self, reservation_id: str) -> DemoReservation: ...

    def consume(
        self,
        reservation_id: str,
        *,
        identity: DemoRequestIdentity,
        planned_units: int,
        now: datetime | None = None,
    ) -> DemoReservation: ...

    def get(self, reservation_id: str) -> DemoReservation | None: ...

    def expire_stale(self, *, now: datetime) -> list[DemoReservation]: ...

    def persist_cached_result(
        self,
        *,
        identity: DemoRequestIdentity,
        reservation_id: str,
        payload: dict,
        now: datetime | None = None,
    ) -> CachedDemoResult: ...

    def get_cached_result(self, request_fingerprint: str) -> CachedDemoResult | None: ...

    def recover_after_restart(self, *, now: datetime) -> AllowanceRestartReport: ...

    def consume_after_cached_result(
        self,
        reservation_id: str,
        *,
        identity: DemoRequestIdentity,
        planned_units: int,
        now: datetime | None = None,
    ) -> ConsumeAfterCacheResult: ...

    def close(self) -> None: ...
