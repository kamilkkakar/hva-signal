"""InMemory remains default. SQLite enablement does not imply hosted live."""

from app.core.config import Settings
from app.core.job_store import InMemoryJobStore
from app.core.persistence_factory import (
    build_demo_allowance_ledger,
    build_job_store,
    hosted_live_enabled_by_sqlite,
    persistence_defaults_keep_hosted_live_off,
    sqlite_persistence_explicitly_enabled,
)
from app.core.sqlite_job_store import SQLiteJobStore
from app.domain.demo_allowance import disabled_demo_policy
from app.services.demo_allowance_ledger import InMemoryDemoAllowanceLedger
from app.services.sqlite_demo_allowance_ledger import SQLiteDemoAllowanceLedger


def test_settings_defaults_keep_sqlite_and_live_off() -> None:
    assert Settings.model_fields["local_sqlite_persistence_enabled"].default is False
    assert Settings.model_fields["local_sqlite_path"].default == ""
    assert Settings.model_fields["demo_allowance_enabled"].default is False
    assert persistence_defaults_keep_hosted_live_off() is True
    assert hosted_live_enabled_by_sqlite() is False


def test_factory_defaults_to_in_memory() -> None:
    settings = Settings.model_construct(
        local_sqlite_persistence_enabled=False,
        local_sqlite_path="",
        demo_allowance_enabled=False,
    )
    store = build_job_store(settings)
    assert isinstance(store, InMemoryJobStore)
    assert sqlite_persistence_explicitly_enabled(settings) is False
    ledger = build_demo_allowance_ledger(disabled_demo_policy(), settings)
    assert isinstance(ledger, InMemoryDemoAllowanceLedger)


def test_flag_without_path_stays_in_memory() -> None:
    settings = Settings.model_construct(
        local_sqlite_persistence_enabled=True,
        local_sqlite_path="",
        demo_allowance_enabled=False,
    )
    assert sqlite_persistence_explicitly_enabled(settings) is False
    assert isinstance(build_job_store(settings), InMemoryJobStore)


def test_explicit_sqlite_does_not_enable_hosted_live(tmp_path) -> None:
    settings = Settings.model_construct(
        local_sqlite_persistence_enabled=True,
        local_sqlite_path=str(tmp_path / "local.sqlite"),
        demo_allowance_enabled=False,
        demo_allowance_max_total_units=0,
    )
    store = build_job_store(settings)
    assert isinstance(store, SQLiteJobStore)
    assert store.hosted_live_implied is False
    assert hosted_live_enabled_by_sqlite(settings) is False
    assert settings.demo_allowance_enabled is False
    ledger = build_demo_allowance_ledger(disabled_demo_policy(), settings)
    assert isinstance(ledger, SQLiteDemoAllowanceLedger)
    assert ledger.hosted_live_implied is False
    store.close()
    ledger.close()
