"""Final frozen spatial decomposition for Gate 0.

Uses existing sanitized FortyGuard fixtures only. No network/API access.
Primary condition: 2024-07-15 03:00 Phoenix local. The identical computation
is also applied secondarily to the existing full-day tile minimum fixture.

This script is the final spatial analytical act for this Gate 0 cycle.
"""

from __future__ import annotations

import json
import math
from pathlib import Path
from typing import Any

import numpy as np
from shapely.geometry import shape

ROOT = Path(__file__).resolve().parents[1]
GATE0 = ROOT / "workforce" / "gate0"
OUT = GATE0 / "final_spatial_audit"
AOIS_PATH = GATE0 / "track_a" / "aois_preregistered.json"
FIXTURE_DIR = GATE0 / "nighttime" / "raw_sanitized"

NA_CONSTANT = "NOT APPLICABLE — CONSTANT FIELD"
NA_TOPOLOGY = "NOT ASSESSABLE — ROOK TOPOLOGY UNAVAILABLE"
PERMUTATIONS = 999
SEED = 20260828
# Treat line intersections at floating-point coordinate epsilon as numerical
# zero, not a shared edge. This enforces rook (edge), rather than accidental
# point/corner contact represented as a microscopic line sliver.
ROOK_NUMERIC_ZERO_DEGREES = 1e-12

CONDITIONS = {
    "03:00": {
        "suffix": "_0300.json",
        "stat_key": "average_temperature",
        "role": "PRIMARY",
    },
    "night_min": {
        "suffix": "_full_day_min.json",
        "stat_key": "min_temperature",
        "role": "SECONDARY — IDENTICAL COMPUTATION",
    },
}


def decimal_places(value: Any) -> int | None:
    if value is None:
        return None
    if isinstance(value, int):
        return 0
    text = format(value, ".16g") if isinstance(value, float) else str(value)
    if "e" in text.lower():
        return None
    if "." not in text:
        return 0
    return len(text.split(".", 1)[1].rstrip("0")) or 0


def sample_sd(values: np.ndarray) -> float:
    if len(np.unique(values)) == 1:
        return 0.0
    return float(np.std(values, ddof=1)) if len(values) > 1 else 0.0


def pearson(left: np.ndarray, right: np.ndarray) -> float:
    return float(np.corrcoef(left, right)[0, 1])


def smallest_increment(values: np.ndarray) -> float | None:
    unique = np.unique(values)
    if len(unique) < 2:
        return None
    differences = np.diff(np.sort(unique))
    positive = differences[differences > 0]
    return float(np.min(positive)) if len(positive) else None


def rook_weights(polygons: list[Any]) -> tuple[np.ndarray | None, dict[str, Any]]:
    """Construct binary rook adjacency from non-zero shared boundary length."""
    n = len(polygons)
    adjacency = np.zeros((n, n), dtype=float)
    invalid = [i for i, polygon in enumerate(polygons) if not polygon.is_valid]
    if invalid:
        return None, {
            "status": NA_TOPOLOGY,
            "reason": f"invalid tile polygons at indices {invalid}",
        }

    shared_edge_lengths: list[float] = []
    for i in range(n):
        for j in range(i + 1, n):
            shared = polygons[i].boundary.intersection(polygons[j].boundary)
            length = float(shared.length)
            if length > ROOK_NUMERIC_ZERO_DEGREES:
                adjacency[i, j] = 1.0
                adjacency[j, i] = 1.0
                shared_edge_lengths.append(length)

    degrees = adjacency.sum(axis=1)
    islands = np.flatnonzero(degrees == 0).tolist()
    if not shared_edge_lengths or islands:
        return None, {
            "status": NA_TOPOLOGY,
            "reason": (
                "no non-zero shared edges"
                if not shared_edge_lengths
                else f"rook graph has isolated tile indices {islands}"
            ),
            "edge_count": int(adjacency.sum() / 2),
            "island_indices": islands,
        }

    row_standardized = adjacency / degrees[:, None]
    return row_standardized, {
        "status": "ASSESSED",
        "edge_count": int(adjacency.sum() / 2),
        "island_count": 0,
        "degree_min": int(degrees.min()),
        "degree_max": int(degrees.max()),
        "shared_edge_length_min_degrees": min(shared_edge_lengths),
        "shared_edge_length_max_degrees": max(shared_edge_lengths),
    }


def moran_i(values: np.ndarray, weights: np.ndarray) -> float:
    centered = values - np.mean(values)
    denominator = float(centered @ centered)
    if denominator == 0:
        raise ValueError("Moran's I undefined for a constant vector")
    s0 = float(weights.sum())
    return float((len(values) / s0) * ((weights * np.outer(centered, centered)).sum() / denominator))


def permutation_diagnostic(
    residuals: np.ndarray, weights: np.ndarray, observed_i: float
) -> dict[str, Any]:
    """Fixed upper-tail test for positive residual spatial autocorrelation."""
    rng = np.random.default_rng(SEED)
    permuted = np.empty(PERMUTATIONS, dtype=float)
    for index in range(PERMUTATIONS):
        permuted[index] = moran_i(rng.permutation(residuals), weights)
    p_upper = float((1 + np.count_nonzero(permuted >= observed_i)) / (PERMUTATIONS + 1))
    expected = -1.0 / (len(residuals) - 1)
    return {
        "permutations": PERMUTATIONS,
        "seed": SEED,
        "test": "upper-tail pseudo-p for positive residual spatial autocorrelation",
        "expected_i_randomization": expected,
        "pseudo_p_upper": p_upper,
        "permuted_i_min": float(permuted.min()),
        "permuted_i_max": float(permuted.max()),
        "permuted_i_mean": float(permuted.mean()),
    }


def load_condition(aoi_id: str, config: dict[str, str]) -> tuple[list[dict[str, Any]], Path]:
    path = FIXTURE_DIR / f"{aoi_id}{config['suffix']}"
    document = json.loads(path.read_text(encoding="utf-8"))
    return list(document["result"]["map_data"]["features"]), path


def assess(aoi: dict[str, Any], condition: str, config: dict[str, str]) -> dict[str, Any]:
    features, path = load_condition(aoi["aoi_id"], config)
    raw_values = [(feature.get("properties") or {}).get(config["stat_key"]) for feature in features]
    values = np.asarray([float(value) for value in raw_values], dtype=float)
    polygons = [shape(feature["geometry"]) for feature in features]
    centroids = [polygon.centroid for polygon in polygons]
    longitude = np.asarray([point.x for point in centroids], dtype=float)
    latitude = np.asarray([point.y for point in centroids], dtype=float)
    unique_count = int(len(np.unique(values)))
    places = [decimal_places(value) for value in raw_values]
    places = [place for place in places if place is not None]

    raw = {
        "tile_count": len(features),
        "unique_value_count": unique_count,
        "minimum": float(values.min()),
        "maximum": float(values.max()),
        "range": float(np.ptp(values)),
        "sample_sd": sample_sd(values),
        "smallest_observed_numeric_increment": smallest_increment(values),
        "representation": {
            "json_types": sorted({type(value).__name__ for value in raw_values}),
            "decimal_places_min": min(places) if places else None,
            "decimal_places_max": max(places) if places else None,
        },
    }

    result: dict[str, Any] = {
        "aoi_id": aoi["aoi_id"],
        "label": aoi["label"],
        "condition": condition,
        "condition_role": config["role"],
        "fixture": str(path.relative_to(ROOT)),
        "constant_field": unique_count == 1,
        "raw": raw,
    }

    if unique_count == 1:
        result.update(
            {
                "constant_value": float(values[0]),
                "coordinate_relationships": {
                    "pearson_value_longitude": NA_CONSTANT,
                    "pearson_value_latitude": NA_CONSTANT,
                },
                "plane": {
                    "beta_0": NA_CONSTANT,
                    "beta_1_longitude_c_per_degree": NA_CONSTANT,
                    "beta_2_latitude_c_per_degree": NA_CONSTANT,
                    "r_squared": NA_CONSTANT,
                    "adjusted_r_squared": NA_CONSTANT,
                },
                "residual": {
                    "mean": NA_CONSTANT,
                    "sample_sd": NA_CONSTANT,
                    "minimum": NA_CONSTANT,
                    "maximum": NA_CONSTANT,
                    "range": NA_CONSTANT,
                    "range_over_observed_increment": NA_CONSTANT,
                },
                "rook_topology": NA_CONSTANT,
                "morans_i": NA_CONSTANT,
                "permutation_diagnostic": NA_CONSTANT,
                "residual_organization_classification": "CONSTANT FIELD",
                "evidence_interpretation": (
                    "Constant field: no within-AOI spatial variation is present "
                    "in this fixture at this condition."
                ),
            }
        )
        return result

    x_center = longitude - longitude.mean()
    y_center = latitude - latitude.mean()
    design = np.column_stack([np.ones(len(values)), x_center, y_center])
    coefficients, _, _, _ = np.linalg.lstsq(design, values, rcond=None)
    fitted = design @ coefficients
    residuals = values - fitted
    total_ss = float(np.sum((values - values.mean()) ** 2))
    residual_ss = float(np.sum(residuals**2))
    r_squared = 1.0 - residual_ss / total_ss
    predictors = 2
    adjusted_r_squared = 1.0 - (1.0 - r_squared) * (len(values) - 1) / (
        len(values) - predictors - 1
    )
    increment = raw["smallest_observed_numeric_increment"]
    residual_range = float(np.ptp(residuals))

    result["coordinate_relationships"] = {
        "pearson_value_longitude": pearson(values, longitude),
        "pearson_value_latitude": pearson(values, latitude),
    }
    result["plane"] = {
        "coordinate_center_longitude": float(longitude.mean()),
        "coordinate_center_latitude": float(latitude.mean()),
        "beta_0_at_coordinate_center": float(coefficients[0]),
        "beta_1_longitude_c_per_degree": float(coefficients[1]),
        "beta_2_latitude_c_per_degree": float(coefficients[2]),
        "r_squared": float(r_squared),
        "adjusted_r_squared": float(adjusted_r_squared),
    }
    result["residual"] = {
        "mean": float(residuals.mean()),
        "sample_sd": sample_sd(residuals),
        "minimum": float(residuals.min()),
        "maximum": float(residuals.max()),
        "range": residual_range,
        "range_over_observed_increment": (
            float(residual_range / increment) if increment is not None else None
        ),
    }

    weights, topology = rook_weights(polygons)
    result["rook_topology"] = topology
    if weights is None:
        result["morans_i"] = NA_TOPOLOGY
        result["permutation_diagnostic"] = NA_TOPOLOGY
        result["residual_organization_classification"] = "NOT ASSESSABLE"
        result["evidence_interpretation"] = (
            "Residual spatial organization is not assessable because valid rook "
            "topology was unavailable. Record as FUTURE VALIDATION / IMPLEMENTATION ISSUE."
        )
        return result

    observed_i = moran_i(residuals, weights)
    permutation = permutation_diagnostic(residuals, weights, observed_i)
    organized = observed_i > permutation["expected_i_randomization"] and permutation["pseudo_p_upper"] <= 0.05
    result["morans_i"] = observed_i
    result["permutation_diagnostic"] = permutation
    result["residual_organization_classification"] = (
        "SPATIALLY ORGANIZED" if organized else "SCATTERED / WEAKLY ORGANIZED"
    )

    if organized:
        result["evidence_interpretation"] = (
            "Observed within-AOI variation includes spatial organization not "
            "summarized by a simple coordinate plane. This does not establish "
            "effective 100 m physical resolution."
        )
    elif r_squared >= 0.95:
        result["evidence_interpretation"] = (
            "Observed within-AOI variation exists, but this fixture provides "
            "limited evidence for fine-grained localization beyond a broad spatial gradient."
        )
    else:
        result["evidence_interpretation"] = (
            "Variation remains after removing a simple spatial plane, but the "
            "residual does not demonstrate clear spatial organization."
        )
    return result


def main() -> int:
    aois = json.loads(AOIS_PATH.read_text(encoding="utf-8"))["aois"]
    results = [
        assess(aoi, condition, config)
        for condition, config in CONDITIONS.items()
        for aoi in aois
    ]
    primary = [result for result in results if result["condition"] == "03:00"]

    payload = {
        "status": "FINAL — SPATIAL GATE 0 ANALYSIS FROZEN AFTER THIS AUDIT",
        "gate0_closed": False,
        "no_new_fortyguard_calls": True,
        "fixtures_only": True,
        "broad_metro_uniqueness": "NO — FROZEN",
        "current_operating_product_outcome": "C — UNDER CURRENT EVIDENCE",
        "superseded_taxonomy": (
            "SUPERSEDED — CONFLATED OBSERVED VARIATION WITH EFFECTIVE SPATIAL LOCALIZATION"
        ),
        "claim_s1_observed_within_aoi_spatial_variation": "YES — IN SOME TESTED AOIs",
        "claim_s2_demonstrated_effective_100m_localization": "NOT ESTABLISHED",
        "classification_rule_frozen_before_results": (
            "SPATIALLY ORGANIZED iff residual Moran's I exceeds its randomization "
            "expectation and fixed upper-tail 999-permutation pseudo-p <= 0.05; "
            "otherwise SCATTERED / WEAKLY ORGANIZED. Descriptive only; not a Gate 0 band."
        ),
        "methods": {
            "primary_condition": "2024-07-15 03:00 Phoenix local",
            "secondary_condition": "existing full-day tile min; identical computation",
            "plane": "TCM = beta0 + beta1(longitude) + beta2(latitude) + residual",
            "rook": (
                "binary polygon-boundary shared non-zero-length edge; row-standardized; "
                "floating-point line slivers <= 1e-12 degrees treated as numerical zero; "
                "no alternative weights"
            ),
            "permutations": PERMUTATIONS,
            "seed": SEED,
            "interpretation_ceiling": (
                "organized residuals show only that a coordinate plane does not "
                "capture all spatial organization; effective 100 m resolution remains unestablished"
            ),
        },
        "primary_03h": primary,
        "secondary_night_min": [
            result for result in results if result["condition"] == "night_min"
        ],
        "unknown_future_validation_vendor_dependent": [
            "TCM physical semantics",
            "effective spatial support of requested 100 m output",
            "meaning of constant spatial blocks",
            "relationship between requested granularity and underlying model support",
            "whether hackathon-tier behavior differs from production",
            "any rook-topology implementation issue identified by this frozen computation",
        ],
        "next_step": "HUMAN PRODUCT DECISION",
        "vendor_wait_cutoff": "2026-08-31",
    }

    OUT.mkdir(parents=True, exist_ok=True)
    output = OUT / "FINAL_SPATIAL_AUDIT.json"
    output.write_text(json.dumps(payload, indent=2, ensure_ascii=False), encoding="utf-8")
    print(f"wrote {output}")
    for result in primary:
        print(
            result["aoi_id"],
            f"constant={result['constant_field']}",
            f"R2={result['plane']['r_squared']}",
            f"I={result['morans_i']}",
            result["residual_organization_classification"],
        )
    print("SPATIAL GATE 0 ANALYSIS IS FROZEN")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
