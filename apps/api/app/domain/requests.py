"""Analysis request and scenario stub contracts."""

from datetime import datetime
from typing import Annotated, Any, Literal

from pydantic import BaseModel, ConfigDict, Field, model_validator

from app.domain.client_privilege import CLIENT_NEVER_SET_FIELDS
from app.domain.enums import AnalysisMode, DataMode
from app.domain.public_safety_fields import (
    CLIENT_CONTROL_FIELD_NAMES,
    classify_client_control_field,
)
from app.services.allowance_client_denylist import (
    CLIENT_NEVER_SET_ALLOWANCE_KEYS,
    walk_payload_keys,
)

_UNPUBLISHED_SIGNAL_B_FIELDS = frozenset(
    {
        "selected_time_snapshot",
        "selected_time",
        "signal_b",
        "snapshot",
        "prepare",
        "prepare_reference",
        "live_snapshot",
        "signals",
        "spend_authorization",
        "spend",
        "approval",
        "contract_version",
        "authorized_max_units",
        "approved",
        "authorize",
        "authorized",
        "skip_approval",
        "admin",
        "operator_override",
        "spend_authorized",
        "demo",
        "demo_test",
        "live_demo",
        "force_live",
        "allowance",
        "allowance_cap",
        "budget",
        "demo_budget",
        "internal_key",
        "key",
        "operator_approval",
        "reservation_state",
        "reservation_id",
        "acquisition_preference",
        "bypass_limit",
        "allowance_remaining",
    }
    | CLIENT_CONTROL_FIELD_NAMES
    | CLIENT_NEVER_SET_FIELDS
    | CLIENT_NEVER_SET_ALLOWANCE_KEYS
)


def _privilege_hits_anywhere(data: Any) -> list[str]:
    """Walk nested mappings. extra=allow wrappers cannot hide privilege names."""
    if not isinstance(data, dict):
        return []
    hits: set[str] = set()
    for key in walk_payload_keys(data):
        classified = classify_client_control_field(str(key))
        if classified is not None:
            hits.add(classified[0])
            continue
        folded = str(key).strip().lower().replace("-", "_")
        if folded in _UNPUBLISHED_SIGNAL_B_FIELDS or str(key) in _UNPUBLISHED_SIGNAL_B_FIELDS:
            hits.add(folded)
    return sorted(hits)


class ScenarioRequest(BaseModel):
    """Typed scenario request stub. Scenario evaluation is owned by Agent F."""

    model_config = ConfigDict(extra="allow")

    scenario_id: str | None = None
    intervention_ids: list[str] = Field(default_factory=list)

    @model_validator(mode="before")
    @classmethod
    def _reject_privilege_extras(cls, data: Any) -> Any:
        hits = _privilege_hits_anywhere(data)
        if hits:
            raise ValueError(
                "unpublished two-signal request fields are not accepted: "
                + ", ".join(hits)
            )
        return data


class AnalysisRequest(BaseModel):
    area_id: str
    analysis_time: datetime
    analysis_mode: AnalysisMode
    horizon_hours: Annotated[int, Field(ge=0, le=12)]
    lookback_hours: Annotated[int, Field(ge=0, le=24 * 31)] = 0
    granularity_m: Literal[60, 80, 100]
    data_mode: DataMode = DataMode.AUTO
    scenario: ScenarioRequest | None = None

    @model_validator(mode="before")
    @classmethod
    def _reject_unpublished_signal_b(cls, data: Any) -> Any:
        hits = _privilege_hits_anywhere(data)
        if hits:
            raise ValueError(
                "unpublished two-signal request fields are not accepted: "
                + ", ".join(hits)
            )
        return data
