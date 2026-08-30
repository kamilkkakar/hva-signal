"""Analysis request and scenario stub contracts."""

from datetime import datetime
from typing import Annotated, Any, Literal

from pydantic import BaseModel, ConfigDict, Field, model_validator

from app.domain.client_privilege import CLIENT_NEVER_SET_FIELDS
from app.domain.enums import AnalysisMode, DataMode
from app.domain.public_safety_fields import CLIENT_CONTROL_FIELD_NAMES
from app.services.allowance_client_denylist import CLIENT_NEVER_SET_ALLOWANCE_KEYS

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


class ScenarioRequest(BaseModel):
    """Typed scenario request stub. Scenario evaluation is owned by Agent F."""

    model_config = ConfigDict(extra="allow")

    scenario_id: str | None = None
    intervention_ids: list[str] = Field(default_factory=list)

    @model_validator(mode="before")
    @classmethod
    def _reject_privilege_extras(cls, data: Any) -> Any:
        if isinstance(data, dict):
            hits = _UNPUBLISHED_SIGNAL_B_FIELDS.intersection(data)
            if hits:
                raise ValueError(
                    "unpublished two-signal request fields are not accepted: "
                    + ", ".join(sorted(hits))
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
        if isinstance(data, dict):
            hits = _UNPUBLISHED_SIGNAL_B_FIELDS.intersection(data)
            if hits:
                raise ValueError(
                    "unpublished two-signal request fields are not accepted: "
                    + ", ".join(sorted(hits))
                )
        return data
