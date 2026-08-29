"""Architecture v0.4 enumerations. String values are the frozen contract."""

from enum import Enum


class TileAssignmentMethod(str, Enum):
    CENTROID_WITHIN = "centroid_within"
    AREA_WEIGHTED = "area_weighted"


class ZoneAggregationStatistic(str, Enum):
    MEAN = "mean"
    P90 = "p90"
    MAX = "max"


class ThermalStatistic(str, Enum):
    INSTANT = "instant"
    MIN = "min"
    MEAN = "mean"
    MAX = "max"


class UpstreamTimeSemantics(str, Enum):
    AOI_LOCAL_TIME = "aoi_local_time"


class HeatmapTemporalMode(str, Enum):
    SINGLE_HOUR = "single_hour"
    HOUR_RANGE = "hour_range"
    FULL_DAY = "full_day"
    DAY_RANGE = "day_range"
    MONTH = "month"


class ThermalDataSource(str, Enum):
    FORTYGUARD_LIVE = "fortyguard_live"
    FORTYGUARD_CACHED = "fortyguard_cached"
    REPLAY = "replay"


class AnalysisMode(str, Enum):
    OPERATIONAL = "operational"
    RETROSPECTIVE = "retrospective"


class DataMode(str, Enum):
    LIVE = "live"
    REPLAY = "replay"
    AUTO = "auto"


class ReferenceFrame(str, Enum):
    ABSOLUTE = "absolute"
    HISTORICAL = "historical"
    RELATIVE = "relative"


class JobStatus(str, Enum):
    QUEUED = "queued"
    LOADING_CONTEXT = "loading_context"
    FETCHING_THERMAL = "fetching_thermal"
    ASSEMBLING_PARTITIONS = "assembling_partitions"
    AGGREGATING_ZONES = "aggregating_zones"
    NORMALIZING = "normalizing"
    VALIDATING_HAZARD_SPREAD = "validating_hazard_spread"
    COMPUTING = "computing"
    COMPLETE = "complete"
    PARTIAL = "partial"
    FAILED = "failed"
    UNKNOWN_JOB = "unknown_job"


class ResultStatus(str, Enum):
    OK = "ok"
    INSUFFICIENT_EVIDENCE = "insufficient_evidence"
    FAILED = "failed"
    PARTIAL = "partial"


class DataStatus(str, Enum):
    LIVE = "live"
    CACHED = "cached"
    REPLAY = "replay"
    PARTIAL = "partial"
    UNAVAILABLE = "unavailable"


class SystemLimitationCode(str, Enum):
    THERMAL_SPATIAL_DIFFERENTIATION_INSUFFICIENT = (
        "THERMAL_SPATIAL_DIFFERENTIATION_INSUFFICIENT"
    )
    INSUFFICIENT_REFERENCE = "INSUFFICIENT_REFERENCE"


class ReferenceEvidenceQuality(str, Enum):
    FULL_REFERENCE = "FULL_REFERENCE"
    INSUFFICIENT_REFERENCE = "INSUFFICIENT_REFERENCE"


class ReferenceRangeStatus(str, Enum):
    BELOW = "BELOW"
    WITHIN = "WITHIN"
    ABOVE = "ABOVE"


class ThermalDifferentiationState(str, Enum):
    SUFFICIENT = "SUFFICIENT"
    INSUFFICIENT = "INSUFFICIENT"
    NOT_EVALUATED = "NOT_EVALUATED"
