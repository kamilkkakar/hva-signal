/** Selected-time snapshot + historical section types. Unpublished P2 shape. */

export const TWO_SIGNAL_CONTRACT_VERSION = "hva-signal-two-signal-job-v1" as const;
export const SELECTED_TIME_TITLE = "Selected-Time Thermal Snapshot" as const;
export const SIGNAL_A_FROZEN_HOUR = "03:00" as const;
export const EXPECTED_ZONE_COUNT = 25;
export const COMBINED_SCORE_AUTHORIZED = false;

export type HistoricalAvailability =
  | "NOT_REQUESTED"
  | "NOT_PREPARED"
  | "PENDING"
  | "READY"
  | "INSUFFICIENT_REFERENCE"
  | "INSUFFICIENT_EVIDENCE"
  | "D8_INSUFFICIENT"
  | "FAILED";

export type SelectedTimeAvailability =
  | "NOT_REQUESTED"
  | "READY"
  | "PENDING"
  | "FETCHING"
  | "PARTIAL"
  | "UNAVAILABLE"
  | "FAILED";

export type SelectedTimeProvenanceSource =
  | "replay"
  | "fortyguard_cached"
  | "fortyguard_live"
  | null;

export type SelectedTimeReadyScene = "cached" | "ready";

export type SnapshotZone = {
  zone_id: string;
  mean_temperature_c: number | null;
  coverage_status: "valid" | "missing";
};

export type HistoricalSection = {
  kind: "historical_normalized";
  requested: boolean;
  availability: HistoricalAvailability;
  frozen_hour: typeof SIGNAL_A_FROZEN_HOUR;
  reason_code: string | null;
};

export type SelectedTimeSection = {
  kind: "selected_time_snapshot";
  requested: boolean;
  availability: SelectedTimeAvailability;
  provenance_source: SelectedTimeProvenanceSource;
  data_status: "replay" | "cached" | "live" | "partial" | "unavailable" | null;
  target_timestamp: string | null;
  timezone: string | null;
  expected_zone_count: number;
  valid_zone_count: number | null;
  missing_zone_ids: string[];
  zones: SnapshotZone[];
  temperature_min_c: number | null;
  temperature_max_c: number | null;
  reason_code: string | null;
  reference_version: null;
  reference_source: null;
  ready_scene?: SelectedTimeReadyScene;
};

export type SignalAUx =
  | "historical_not_requested"
  | "historical_not_prepared"
  | "historical_pending"
  | "historical_ready"
  | "historical_insufficient"
  | "historical_failed";

export type SignalBUx =
  | "b_not_requested"
  | "b_cached"
  | "b_unavailable"
  | "b_fetching"
  | "b_partial"
  | "b_ready"
  | "live_demo_confirmation";

export type SignalATone =
  | "inert"
  | "not-prepared"
  | "pending"
  | "historical"
  | "insufficient"
  | "failed";

export type SignalBSourceLabel =
  | "REPLAY"
  | "CACHED"
  | "UNAVAILABLE"
  | "FETCHING"
  | "PARTIAL"
  | "SNAPSHOT";

export type HistoricalView = {
  ux: SignalAUx;
  stamp: string;
  tone: SignalATone;
  availability: HistoricalAvailability;
  copy: string[];
};

export type SelectedTimeView = {
  ux: SignalBUx;
  stamp: string;
  source: SignalBSourceLabel | null;
  availability: SelectedTimeAvailability;
  reuse_only: string;
  copy: string;
  show_live_demo: boolean;
  live_tape: false;
  title: typeof SELECTED_TIME_TITLE;
  zones: SnapshotZone[];
  coverage_label: string | null;
  range_label: string | null;
};

export type TwoSignalView = {
  mounted: boolean;
  combined_score_authorized: false;
  combined_score: null;
  overall_job_complete: false;
  signal_a_blocks_signal_b: false;
  independence_copy: string;
  historical: HistoricalView;
  selected_time: SelectedTimeView;
};
