/** Architecture v0.4 enumerations. Values match the Python domain contracts. */

export type TileAssignmentMethod = "centroid_within" | "area_weighted";

export type ZoneAggregationStatistic = "mean" | "p90" | "max";

export type ThermalStatistic = "instant" | "min" | "mean" | "max";

export type UpstreamTimeSemantics = "aoi_local_time";

export type HeatmapTemporalMode =
  | "single_hour"
  | "hour_range"
  | "full_day"
  | "day_range"
  | "month";

export type ThermalDataSource = "fortyguard_live" | "fortyguard_cached" | "replay";

export type AnalysisMode = "operational" | "retrospective";

export type DataMode = "live" | "replay" | "auto";

export type ReferenceFrame = "absolute" | "historical" | "relative";

export type JobStatus =
  | "queued"
  | "loading_context"
  | "fetching_thermal"
  | "assembling_partitions"
  | "aggregating_zones"
  | "normalizing"
  | "validating_hazard_spread"
  | "computing"
  | "complete"
  | "partial"
  | "failed"
  | "unknown_job";

export type ResultStatus = "ok" | "insufficient_evidence" | "failed" | "partial";

export type DataStatus = "live" | "cached" | "replay" | "partial" | "unavailable";

export type SystemLimitationCode =
  | "THERMAL_SPATIAL_DIFFERENTIATION_INSUFFICIENT"
  | "INSUFFICIENT_REFERENCE";

export type Gate0Status = "not_frozen" | "frozen";
