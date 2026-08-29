"""FortyGuard transport adapter. Engines must not call FortyGuard except through here."""

from app.integrations.fortyguard.adapter import FortyGuardAdapter
from app.integrations.fortyguard.exceptions import (
    ActivityNotReadyError,
    FortyGuardAdapterError,
    MissingApiKeyError,
    ReplayFixtureNotFoundError,
    TaskFailedError,
    TaskTimeoutError,
)
from app.integrations.fortyguard.transport_models import ADAPTER_VERSION

__all__ = [
    "ADAPTER_VERSION",
    "ActivityNotReadyError",
    "FortyGuardAdapter",
    "FortyGuardAdapterError",
    "MissingApiKeyError",
    "ReplayFixtureNotFoundError",
    "TaskFailedError",
    "TaskTimeoutError",
]
