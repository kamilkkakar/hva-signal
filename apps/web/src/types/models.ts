/** Architecture v0.4 domain models. Field names match the Python contracts. */

import type {
  AnalysisMode,
  DataMode,
  DataStatus,
  Gate0Status,
  HeatmapTemporalMode,
  JobStatus,
  ReferenceFrame,
  ResultStatus,
  ThermalDataSource,
  ThermalStatistic,
  TileAssignmentMethod,
  UpstreamTimeSemantics,
  ZoneAggregationStatistic,
} from "./enums";

export type GeoJSONGeometry = Record<string, unknown>;

export interface ThermalAggregationSpec {
  version: string;
  assignment_method: TileAssignmentMethod;
  statistic: ZoneAggregationStatistic;
  minimum_coverage_ratio: number | null;
  zero_tile_behavior: "insufficient_evidence";
  boundary_behavior: string;
  notes: string[];
}

export interface AnalysisZone {
  zone_id: string;
  area_id: string;
  geometry: GeoJSONGeometry;
  geometry_version: string;
  display_name: string | null;
  source: string;
  source_resolution: string | null;
  area_km2: number;
}

export interface UpstreamPartition {
  partition_id: string;
  geometry: GeoJSONGeometry;
  request_fingerprint: string;
  expected_zone_ids: string[];
}

export interface ThermalObservation {
  valid_time: string;
  statistic: ThermalStatistic;
  value: number | null;
  quality_flags: string[];
  evidence_refs: string[];
}

export interface ZoneThermalSeries {
  zone_id: string;
  source: ThermalDataSource;
  temporal_mode: HeatmapTemporalMode;
  upstream_time_semantics: UpstreamTimeSemantics;
  resolution_m: 60 | 80 | 100 | null;
  aggregation_spec_version: string;
  observations: ThermalObservation[];
  tile_count: number;
  expected_tile_count: number | null;
  tile_coverage_ratio: number | null;
  evidence_refs: string[];
  quality_flags: string[];
}

export interface ScenarioRequest {
  scenario_id?: string | null;
  intervention_ids?: string[];
  [key: string]: unknown;
}

export interface AnalysisRequest {
  area_id: string;
  analysis_time: string;
  analysis_mode: AnalysisMode;
  horizon_hours: number;
  lookback_hours: number;
  granularity_m: 60 | 80 | 100;
  data_mode: DataMode;
  scenario: ScenarioRequest | null;
}

export interface NormalizedFeature {
  raw_value: number | null;
  normalized_value: number | null;
  unit: string | null;
  reference_frame: ReferenceFrame;
  reference_definition: string;
  evidence_refs: string[];
  quality_flags: string[];
}

export interface ZoneFeatureVector {
  zone_id: string;
  hazard_peak: NormalizedFeature | null;
  hazard_anomaly: NormalizedFeature | null;
  hazard_duration: NormalizedFeature | null;
  exposure_population: NormalizedFeature | null;
  exposure_critical_facilities: NormalizedFeature | null;
  vulnerability_index: NormalizedFeature | null;
  cooling_access_score: NormalizedFeature | null;
  thermal_burden_score: NormalizedFeature | null;
  intervention_evidence_modifier: NormalizedFeature | null;
  recovery_score: NormalizedFeature | null;
  coverage_ratio: number;
  quality_flags: string[];
  evidence_refs: string[];
}

export interface Confidence {
  score: number;
  band: string;
}

export interface EngineResult<T = unknown> {
  status: ResultStatus;
  value: T | null;
  confidence: Confidence;
  confidence_reasons: string[];
  evidence_refs: string[];
  quality_flags: string[];
  model_version: string;
}

export interface EvidenceNode {
  id: string;
  type: string;
  label: string;
  source_type: string;
  metadata: Record<string, unknown>;
}

export interface EvidenceEdge {
  from_id: string;
  to_id: string;
  relation: string;
}

export interface EvidenceGraph {
  nodes: EvidenceNode[];
  edges: EvidenceEdge[];
}

export interface AnalysisVersions {
  analysis_schema_version: string;
  area_config_version: string;
  zone_definition_version: string;
  zone_geometry_version: string;
  thermal_aggregation_version: string;
  normalization_registry_version: string;
  hazard_spread_policy_version: string;
  probability_model_version: string;
  consequence_model_version: string;
  protection_model_version: string;
  priority_model_version: string;
  thermal_burden_model_version: string | null;
  intervention_evidence_model_version: string | null;
  recovery_model_version: string | null;
  intervention_catalog_version: string;
  context_dataset_version: string;
  fortyguard_adapter_version: string;
  build_commit_sha: string | null;
}

export interface HazardSpreadProvenance {
  policy_version: string;
  reference_version: string | null;
  zone_geometry_version: string | null;
  input_quantity: string | null;
  metric: string;
  top_group_size: number | null;
  bottom_group_size: number | null;
  floor: number | null;
  comparison_operator: string | null;
  observed_spread: number | null;
  differentiation_state: string;
  reference_quality: string;
  suppression_reason: string | null;
  historical_years: number[] | null;
  reference_hour: string | null;
}

export interface ZoneDecisionResult {
  zone_id: string;
  ranked: boolean;
  probability: EngineResult;
  consequence: EngineResult;
  protection: EngineResult;
  priority: EngineResult;
  quality_flags: string[];
  evidence_refs: string[];
  thermal_observation_valid: boolean;
  q_A: number | null;
  reference_range_status: string | null;
  reference_range_exceedance_c: number | null;
  thermal_ordering_permitted: boolean;
}

export interface PortfolioRecommendation {
  summary?: string | null;
  recommended_intervention_ids?: string[];
  evidence_refs?: string[];
  quality_flags?: string[];
  [key: string]: unknown;
}

export interface AnalysisResult {
  analysis_id: string;
  generated_at: string;
  analysis_mode: AnalysisMode;
  versions: AnalysisVersions;
  data_status: DataStatus;
  system_limitations: string[];
  zones: ZoneDecisionResult[];
  portfolio_recommendation: PortfolioRecommendation | null;
  evidence_graph: EvidenceGraph;
  limitations: string[];
  reference_quality: string | null;
  thermal_differentiation_state: string | null;
  hazard_spread: HazardSpreadProvenance | null;
  area_config_sha256?: string | null;
  reference_source_sha256?: string | null;
}

export interface HistoricalReferenceSpec {
  version: string;
  percentile: number | null;
  seasonal_window: string;
  statistic?: string | null;
}

export interface CoveragePolicy {
  version: string;
  minimum_coverage_ratio: number | null;
}

export interface ConfidencePolicy {
  status: "INACTIVE" | "ACTIVE";
  version?: string | null;
  band_cutoffs?: Record<string, number> | null;
}

export interface ModuleFlags {
  intervention_evidence: boolean;
  human_thermal_burden: boolean;
  overnight_recovery: boolean;
}

export interface HazardSpreadPolicy {
  version: string;
  metric: string;
  minimum_useful_spread: number | null;
  behavior_below_floor: "surface_system_limitation";
  input_quantity?: string | null;
  top_group_size?: number | null;
  bottom_group_size?: number | null;
  comparison_operator?: ">=" | null;
  reference_version?: string | null;
  zone_geometry_version?: string | null;
  expected_zone_count?: number | null;
}

export interface AreaConfig {
  _comment?: string | null;
  candidate_status?: string | null;
  area_id: string;
  version: string;
  zone_definition_version: string;
  zone_type: string;
  zone_source: string;
  zone_geometry_version: string;
  expected_zone_count: number;
  /** FortyGuard acquisition/request granularity. Not validated localization. S2 NOT ESTABLISHED. */
  granularity_m: 60 | 80 | 100;
  partition_strategy: string;
  partition_policy_version: string;
  thermal_aggregation: ThermalAggregationSpec;
  default_hazard_reference_frame: ReferenceFrame;
  historical_reference_window: HistoricalReferenceSpec;
  coverage_policy: CoveragePolicy;
  confidence_policy: ConfidencePolicy;
  hazard_spread_policy: HazardSpreadPolicy;
  intervention_catalog_version: string | null;
  intervention_cost_profile: Record<string, unknown> | null;
  intervention_lead_time_profile: Record<string, unknown> | null;
  module_flags: ModuleFlags;
  gate0_status: Gate0Status;
}

export interface InterventionDefinition {
  intervention_id: string;
  name: string;
  catalog_version: string;
  cost_profile_key?: string | null;
  lead_time_profile_key?: string | null;
  reversibility?: string | null;
  evidence_refs?: string[];
  quality_flags?: string[];
  [key: string]: unknown;
}

export interface AnalysisJob {
  job_id: string;
  status: JobStatus;
  request: AnalysisRequest;
  created_at: string;
  recoverable: boolean;
  message: string | null;
}
