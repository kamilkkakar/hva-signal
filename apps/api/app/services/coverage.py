"""Tile coverage evaluation for zone aggregation."""

from __future__ import annotations

from dataclasses import dataclass

INSUFFICIENT_EVIDENCE = "insufficient_evidence"
RESULT_OK = "ok"


@dataclass(frozen=True)
class CoverageEvaluation:
    tile_coverage_ratio: float | None
    ranked: bool
    result_status: str
    quality_flags: list[str]


def compute_tile_coverage_ratio(
    assigned_count: int,
    expected_count: float | None,
) -> float | None:
    """Return assigned / expected tile coverage, or None when expected is unset."""
    if expected_count is None or expected_count <= 0:
        return None
    return assigned_count / expected_count


def evaluate_coverage(
    assigned_count: int,
    expected_count: float | None,
    minimum_coverage_ratio: float | None,
    *,
    zero_tile_behavior: str = INSUFFICIENT_EVIDENCE,
) -> CoverageEvaluation:
    """Apply coverage policy: zero tiles always insufficient; numeric floor optional.

    ``minimum_coverage_ratio is None`` means no numeric ratio floor is
    operationalized. Observed ratio may still be returned as evidence.
    """
    if assigned_count == 0:
        return CoverageEvaluation(
            tile_coverage_ratio=compute_tile_coverage_ratio(0, expected_count),
            ranked=False,
            result_status=zero_tile_behavior,
            quality_flags=[zero_tile_behavior],
        )

    ratio = compute_tile_coverage_ratio(assigned_count, expected_count)
    if minimum_coverage_ratio is None or ratio is None:
        return CoverageEvaluation(
            tile_coverage_ratio=ratio,
            ranked=True,
            result_status=RESULT_OK,
            quality_flags=[],
        )

    if ratio < minimum_coverage_ratio:
        return CoverageEvaluation(
            tile_coverage_ratio=ratio,
            ranked=False,
            result_status=INSUFFICIENT_EVIDENCE,
            quality_flags=[INSUFFICIENT_EVIDENCE],
        )

    return CoverageEvaluation(
        tile_coverage_ratio=ratio,
        ranked=True,
        result_status=RESULT_OK,
        quality_flags=[],
    )
