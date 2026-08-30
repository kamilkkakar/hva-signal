"""Restart recovery for demo allowance. Reserve ≠ consume. No paid auto-resume."""

from __future__ import annotations

from datetime import datetime

from app.domain.demo_allowance import (
    AllowanceRestartReport,
    ConsumeAfterCacheResult,
    DemoRequestIdentity,
)
from app.services.demo_allowance_port import DemoAllowanceLedgerPort


def recover_reservations_after_restart(
    ledger: DemoAllowanceLedgerPort, *, now: datetime
) -> AllowanceRestartReport:
    """Expire stale reserved rows. Do not consume. Do not call a vendor."""
    return ledger.recover_after_restart(now=now)


def recover_after_cache_before_consume(
    ledger: DemoAllowanceLedgerPort,
    *,
    reservation_id: str,
    identity: DemoRequestIdentity,
    planned_units: int,
    now: datetime | None = None,
) -> ConsumeAfterCacheResult:
    """Count the reservation at most once and keep the cached payload."""
    return ledger.consume_after_cached_result(
        reservation_id,
        identity=identity,
        planned_units=planned_units,
        now=now,
    )
