"""Hazard normalization. RELATIVE / AOI min-max is not implemented for hazard."""

from __future__ import annotations

from collections.abc import Sequence

from app.domain.enums import ReferenceFrame
from app.domain.normalization import NormalizedFeature
from app.services.normalization_registry import NORMALIZATION_REGISTRY_VERSION

INSUFFICIENT_EVIDENCE = "insufficient_evidence"

__all__ = [
    "RelativeHazardNormalizationError",
    "normalize_hazard",
]


class RelativeHazardNormalizationError(ValueError):
    """RELATIVE / AOI min-max must not be used for hazard ranking."""


def _empirical_percentile(value: float, baseline: Sequence[float]) -> float:
    """Percent of injected baseline values that are <= value (empirical CDF)."""
    n = len(baseline)
    return 100.0 * sum(1 for sample in baseline if sample <= value) / n


def _feature(
    *,
    raw_value: float | None,
    normalized_value: float | None,
    unit: str | None,
    reference_frame: ReferenceFrame,
    reference_definition: str,
    quality_flags: list[str] | None = None,
    evidence_refs: Sequence[str] | None = None,
) -> NormalizedFeature:
    return NormalizedFeature(
        raw_value=raw_value,
        normalized_value=normalized_value,
        unit=unit,
        reference_frame=reference_frame,
        reference_definition=reference_definition,
        evidence_refs=list(evidence_refs or []),
        quality_flags=list(quality_flags or []),
    )


def normalize_hazard(
    raw_value: float | None,
    reference_frame: ReferenceFrame,
    *,
    baseline_series: Sequence[float] | None = None,
    reference_definition: str | None = None,
    evidence_refs: Sequence[str] | None = None,
) -> NormalizedFeature:
    """Normalize a zone TCM value for hazard. Missing TCM stays None, never 0.

    ABSOLUTE is identity on TCM Celsius. HISTORICAL is a percentile against an
    injected baseline series (caller-supplied fixture or config), not live
    Phoenix climatology. RELATIVE / AOI min-max is rejected for hazard.
    """
    if reference_frame is ReferenceFrame.RELATIVE:
        raise RelativeHazardNormalizationError(
            "RELATIVE / AOI min-max must not be used for hazard ranking."
        )

    refs = list(evidence_refs or [])
    refs.append(f"normalization_registry:{NORMALIZATION_REGISTRY_VERSION}")

    if reference_frame is ReferenceFrame.ABSOLUTE:
        definition = reference_definition or "identity: TCM Celsius (absolute)"
        if raw_value is None:
            return _feature(
                raw_value=None,
                normalized_value=None,
                unit="celsius",
                reference_frame=reference_frame,
                reference_definition=definition,
                quality_flags=[INSUFFICIENT_EVIDENCE],
                evidence_refs=refs,
            )
        return _feature(
            raw_value=float(raw_value),
            normalized_value=float(raw_value),
            unit="celsius",
            reference_frame=reference_frame,
            reference_definition=definition,
            evidence_refs=refs,
        )

    if reference_frame is ReferenceFrame.HISTORICAL:
        definition = reference_definition or (
            "percentile versus injected baseline series "
            f"(registry {NORMALIZATION_REGISTRY_VERSION})"
        )
        if raw_value is None:
            return _feature(
                raw_value=None,
                normalized_value=None,
                unit="percentile",
                reference_frame=reference_frame,
                reference_definition=definition,
                quality_flags=[INSUFFICIENT_EVIDENCE],
                evidence_refs=refs,
            )
        if not baseline_series:
            return _feature(
                raw_value=float(raw_value),
                normalized_value=None,
                unit="percentile",
                reference_frame=reference_frame,
                reference_definition=definition,
                quality_flags=[INSUFFICIENT_EVIDENCE],
                evidence_refs=refs,
            )
        return _feature(
            raw_value=float(raw_value),
            normalized_value=_empirical_percentile(float(raw_value), baseline_series),
            unit="percentile",
            reference_frame=reference_frame,
            reference_definition=definition,
            evidence_refs=refs,
        )

    raise ValueError(f"Unsupported hazard reference frame: {reference_frame!r}")
