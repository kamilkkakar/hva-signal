"""Analysis request and scenario stub contracts."""

from datetime import datetime
from typing import Annotated, Any, Literal

from pydantic import BaseModel, ConfigDict, Field, model_validator

from app.domain.enums import AnalysisMode, DataMode

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
    }
)


class ScenarioRequest(BaseModel):
    """Typed scenario request stub. Scenario evaluation is owned by Agent F."""

    model_config = ConfigDict(extra="allow")

    scenario_id: str | None = None
    intervention_ids: list[str] = Field(default_factory=list)


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
