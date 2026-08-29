"""AreaConfig-supporting policy types. Values stay in versioned config, not code constants."""

from typing import Literal, Self

from pydantic import BaseModel, ConfigDict, model_validator


class HistoricalReferenceSpec(BaseModel):
    version: str
    percentile: float | None = None
    seasonal_window: str
    statistic: str | None = None


def require_historical_percentile(spec: HistoricalReferenceSpec) -> float:
    """Legacy percentile-threshold features must demand a number explicitly.

    Phoenix v1 q_A does not use this field. ``None`` means NOT_APPLICABLE.
    """
    if spec.percentile is None:
        raise ValueError(
            "legacy historical percentile feature requires a numeric percentile; "
            "None is NOT_APPLICABLE (Phoenix v1 q_A does not use a percentile threshold)"
        )
    return spec.percentile


class CoveragePolicy(BaseModel):
    """Canonical AreaConfig coverage-policy source.

    ``minimum_coverage_ratio is None`` means no numeric ratio floor is
    operationalized. Zero valid assigned tiles remain INSUFFICIENT_EVIDENCE.
    This policy does not affect Decision 1B FULL_REFERENCE.
    """

    version: str
    minimum_coverage_ratio: float | None = None


class ConfidencePolicy(BaseModel):
    """Confidence-band policy. Inactive configs must not carry fake cutoffs."""

    status: Literal["INACTIVE", "ACTIVE"] = "INACTIVE"
    version: str | None = None
    band_cutoffs: dict[str, float] | None = None

    @model_validator(mode="after")
    def _inactive_has_no_fabricated_policy(self) -> Self:
        if self.status == "INACTIVE":
            if self.version is not None or self.band_cutoffs is not None:
                raise ValueError(
                    "inactive confidence policy must not carry a version or band_cutoffs"
                )
        elif not self.version or self.band_cutoffs is None:
            raise ValueError(
                "active confidence policy requires version and band_cutoffs"
            )
        return self


class ModuleFlags(BaseModel):
    """Explicit Phoenix/module activation flags. Unknown keys cannot activate silently."""

    model_config = ConfigDict(extra="forbid")

    intervention_evidence: bool = False
    human_thermal_burden: bool = False
    overnight_recovery: bool = False


class HazardSpreadPolicy(BaseModel):
    version: str
    metric: str
    minimum_useful_spread: float | None = None
    behavior_below_floor: Literal["surface_system_limitation"] = (
        "surface_system_limitation"
    )
    input_quantity: str | None = None
    top_group_size: int | None = None
    bottom_group_size: int | None = None
    comparison_operator: Literal[">="] | None = None
    reference_version: str | None = None
    zone_geometry_version: str | None = None
    expected_zone_count: int | None = None
