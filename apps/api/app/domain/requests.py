"""Analysis request and scenario stub contracts."""

from datetime import datetime
from typing import Annotated, Literal

from pydantic import BaseModel, ConfigDict, Field

from app.domain.enums import AnalysisMode, DataMode


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
