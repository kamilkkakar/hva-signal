export const PUBLIC_PROVENANCE_CONTRACT_VERSION =
  "hva-signal-public-provenance-v1" as const;

export type SignalKind = "historical_normalized" | "selected_time_snapshot";

export type ProvenanceSource = "fortyguard_live" | "fortyguard_cached" | "replay";

export type ProvenanceDataStatus =
  | "live"
  | "cached"
  | "replay"
  | "partial"
  | "unavailable";

export type ProvenanceBannerLabel =
  | "FORTYGUARD LIVE"
  | "FORTYGUARD CACHED"
  | "REPLAY"
  | "PARTIAL"
  | "UNAVAILABLE";

export type PublicSignalProvenance = {
  contract_version?: typeof PUBLIC_PROVENANCE_CONTRACT_VERSION;
  signal_kind: SignalKind;
  source?: ProvenanceSource | null;
  data_status?: ProvenanceDataStatus | null;
  target_timestamp?: string | null;
  timezone?: string | null;
  geometry_version?: string | null;
  geometry_sha256?: string | null;
  aggregation_spec_version?: string | null;
  reference_version?: string | null;
  reference_source?: string | null;
  request_fingerprint?: string | null;
  availability?: string | null;
};

export const A_REQUIRED_WHEN_COMPUTED = [
  "source",
  "data_status",
  "target_timestamp",
  "timezone",
  "geometry_version",
  "aggregation_spec_version",
  "reference_source",
  "reference_version",
] as const;

export const B_REQUIRED_WHEN_PATH_KNOWN = [
  "source",
  "data_status",
  "target_timestamp",
  "timezone",
  "geometry_version",
  "geometry_sha256",
  "aggregation_spec_version",
] as const;

export const B_FORBIDDEN_FIELDS = [
  "reference_version",
  "reference_source",
  "reference_source_sha256",
  "hazard_spread",
  "q_A",
  "historical_result",
  "decision8",
] as const;

export const B_FORBIDDEN_COPY = [
  "Reference:",
  "reference_version",
  "Decision 8",
  "decision8",
  "q_A",
  "NOW",
  "current conditions",
] as const;

export const A_NOT_PREPARED_COPY =
  "Historical nighttime signal is not prepared for this analysis window.";

export const PHOENIX_AGGREGATION_SPEC =
  "PHX_THERMAL_AGGREGATION_V1_CENTROID_WITHIN_MEAN";

export const NATIONAL_AGGREGATION_SPEC =
  "HVA_NATIONAL_THERMAL_AGGREGATION_V1_CENTROID_WITHIN_MEAN";
