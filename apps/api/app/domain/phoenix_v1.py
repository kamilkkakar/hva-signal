"""Frozen Phoenix v1 Decision 1B / Decision 8 identifiers.

These constants make the runtime capable of consuming the already-frozen
policies. Phoenix v1 AreaConfig is HUMAN-FROZEN as PHX_AREA_CONFIG_V1.
Decision 9 is CLOSED. Gate 0 remains NOT READY TO CLOSE.
"""

from __future__ import annotations

from datetime import date

from app.domain.policies import HazardSpreadPolicy

AREA_CONFIG_VERSION = "PHX_AREA_CONFIG_V1"
AREA_ID = "phoenix-demo"
FROZEN_AREA_CONFIG_SHA256 = (
    "df00333a4df900a9762b7be975ed0c36b6e1749c953e9fb4690d9f6e4e02a60a"
)
FROZEN_STATUS = "HUMAN-FROZEN"
FROZEN_COMMENT = (
    "HUMAN-FROZEN. Decision 9 CLOSED. gate0_status=frozen. "
    "PHX_AREA_CONFIG_V1. No semantic AreaConfig values changed during freeze."
)

ZONE_TYPE = "census_tract"
ZONE_DEFINITION_VERSION = "US_CENSUS_TIGERLINE.CENSUS_TRACT.2025.AZ"
ZONE_SOURCE = (
    "U.S. Census Bureau 2025 TIGER/Line Census Tracts, Arizona "
    "(tl_2025_04_tract.zip, FIPS 04)"
)
ZONE_GEOMETRY_VERSION = (
    "US_CENSUS_TIGERLINE.CENSUS_TRACT.2025.AZ.PHX_DEMO_AOI_POLICY_V1.3f16870f"
)
EXPECTED_ZONE_COUNT = 25

GRANULARITY_M = 100
PARTITION_STRATEGY = "single_aoi"
PARTITION_POLICY_VERSION = "PHX_PARTITION_POLICY_V1_SINGLE_AOI"
THERMAL_AGGREGATION_VERSION = "PHX_THERMAL_AGGREGATION_V1_CENTROID_WITHIN_MEAN"
COVERAGE_POLICY_VERSION = (
    "PHX_COVERAGE_POLICY_V1_ZERO_TILE_FAIL_CLOSED_NO_RATIO_FLOOR"
)

REFERENCE_VERSION = (
    "PHX_ZTSI_REF_V1__US_CENSUS_TIGERLINE.CENSUS_TRACT.2025.AZ."
    "PHX_DEMO_AOI_POLICY_V1.3f16870f__ANCHOR_2025-07-15__S2_PM15_CALENDAR_DAYS__"
    "YEARS_2022_2023_2024__HOUR_0300_LOCAL__GRANULARITY_100M"
)
SEASONAL_WINDOW = "06-30 through 07-30 inclusive"
SEASONAL_START_MONTH_DAY = (6, 30)
SEASONAL_END_MONTH_DAY = (7, 30)
REFERENCE_STATISTIC = "YEAR_BALANCED_OWN_TRACT_MIDRANK_ECDF"
REFERENCE_YEARS = (2022, 2023, 2024)
REFERENCE_HOUR_LOCAL = "03:00"
OBS_PER_YEAR = 31
EXPECTED_TIMESTAMPS = 93
REFERENCE_SELF_INCLUSION = "EXCLUDE_TARGET_TIMESTAMP"

DECISION8_POLICY_VERSION = (
    "PHX_NORMALIZED_HAZARD_SPREAD_V1_TOP3_BOTTOM3_QA_FLOOR_0P10"
)
INPUT_QUANTITY = "q_A"
INPUT_QUANTITY_COMPONENT = "temporal_anomaly"
METRIC_TOP3_BOTTOM3 = "TOP3_BOTTOM3_MEAN_DIFFERENCE"
SPREAD_FLOOR = 0.10
TOP_GROUP_SIZE = 3
BOTTOM_GROUP_SIZE = 3
COMPARISON_OPERATOR = ">="


def seasonal_window_length_days() -> int:
    start = date(2023, *SEASONAL_START_MONTH_DAY)
    end = date(2023, *SEASONAL_END_MONTH_DAY)
    return (end - start).days + 1


def decision8_policy_fixture() -> HazardSpreadPolicy:
    """Explicit Decision 8 V1 policy object for tests and production callers.

    Not a substitute for the frozen AreaConfig. Decision 9 is CLOSED.
    """
    return HazardSpreadPolicy(
        version=DECISION8_POLICY_VERSION,
        metric=METRIC_TOP3_BOTTOM3,
        minimum_useful_spread=SPREAD_FLOOR,
        behavior_below_floor="surface_system_limitation",
        input_quantity=INPUT_QUANTITY,
        top_group_size=TOP_GROUP_SIZE,
        bottom_group_size=BOTTOM_GROUP_SIZE,
        comparison_operator=COMPARISON_OPERATOR,
        reference_version=REFERENCE_VERSION,
        zone_geometry_version=ZONE_GEOMETRY_VERSION,
        expected_zone_count=EXPECTED_ZONE_COUNT,
    )


def assert_runtime_matches_frozen_reference() -> None:
    """Fail if production Decision 1B constants disagree with the frozen contract."""
    from app.domain.enums import ReferenceEvidenceQuality

    if REFERENCE_YEARS != (2022, 2023, 2024):
        raise ValueError("runtime REFERENCE_YEARS disagree with frozen contract")
    if REFERENCE_HOUR_LOCAL != "03:00":
        raise ValueError("runtime reference hour disagrees with frozen contract")
    if GRANULARITY_M != 100:
        raise ValueError("runtime granularity disagrees with frozen contract")
    if "GRANULARITY_100M" not in REFERENCE_VERSION:
        raise ValueError("reference version missing GRANULARITY_100M")
    if "YEARS_2022_2023_2024" not in REFERENCE_VERSION:
        raise ValueError("reference version missing years stamp")
    if "HOUR_0300_LOCAL" not in REFERENCE_VERSION:
        raise ValueError("reference version missing hour stamp")
    if "S2_PM15_CALENDAR_DAYS" not in REFERENCE_VERSION:
        raise ValueError("reference version missing seasonal stamp")
    if ZONE_GEOMETRY_VERSION not in REFERENCE_VERSION:
        raise ValueError("reference version missing frozen geometry")
    if seasonal_window_length_days() != OBS_PER_YEAR:
        raise ValueError("seasonal window length disagrees with OBS_PER_YEAR")
    if EXPECTED_TIMESTAMPS != OBS_PER_YEAR * len(REFERENCE_YEARS):
        raise ValueError("timestamp count disagrees with years × seasonal days")
    if REFERENCE_SELF_INCLUSION != "EXCLUDE_TARGET_TIMESTAMP":
        raise ValueError("self-inclusion policy mismatch")
    if "REDUCED_REFERENCE" in ReferenceEvidenceQuality.__members__:
        raise ValueError("REDUCED_REFERENCE must not be operationalized")
