"""Compose job/allowance stores. InMemory is the default.

SQLite is used only when an operator explicitly enables local file
durability AND sets a path. That switch never enables hosted live,
demo allowance, or a vendor adapter.
"""

from __future__ import annotations

from app.core.config import Settings
from app.core.job_store import InMemoryJobStore, JobStore
from app.core.sqlite_job_store import SQLiteJobStore
from app.domain.demo_allowance import DemoAllowancePolicy
from app.services.demo_allowance_ledger import InMemoryDemoAllowanceLedger
from app.services.sqlite_demo_allowance_ledger import SQLiteDemoAllowanceLedger


def sqlite_persistence_explicitly_enabled(settings: Settings) -> bool:
    enabled = bool(getattr(settings, "local_sqlite_persistence_enabled", False))
    path = str(getattr(settings, "local_sqlite_path", "") or "").strip()
    return enabled and bool(path)


def hosted_live_enabled_by_sqlite(settings: Settings | None = None) -> bool:
    """SQLite local durability never implies a live vendor."""
    del settings
    return False


def persistence_defaults_keep_hosted_live_off(settings_cls: type[Settings] = Settings) -> bool:
    fields = settings_cls.model_fields
    return (
        fields["local_sqlite_persistence_enabled"].default is False
        and str(fields["local_sqlite_path"].default or "") == ""
        and fields["demo_allowance_enabled"].default is False
        and int(fields["demo_allowance_max_total_units"].default) == 0
    )


def build_job_store(settings: Settings | None = None) -> JobStore:
    current = settings or Settings()
    if sqlite_persistence_explicitly_enabled(current):
        return SQLiteJobStore(current.local_sqlite_path)
    return InMemoryJobStore()


def build_demo_allowance_ledger(
    policy: DemoAllowancePolicy,
    settings: Settings | None = None,
) -> InMemoryDemoAllowanceLedger | SQLiteDemoAllowanceLedger:
    current = settings or Settings()
    if sqlite_persistence_explicitly_enabled(current):
        return SQLiteDemoAllowanceLedger(policy, current.local_sqlite_path)
    return InMemoryDemoAllowanceLedger(policy)
