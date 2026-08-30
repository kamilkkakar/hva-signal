export type SectionStatus = "AVAILABLE" | "INSUFFICIENT" | "UNKNOWN";

export type MatchedNighttimeView = {
  unpublished?: boolean;
  not_signal_a?: boolean;
  window_label?: string;
  window_start?: string;
  window_end?: string;
  window_dates?: string;
  local_time?: string;
  years?: number[];
  selected_area?: {
    area_id?: string;
    geoid?: string;
    mean_by_year?: Record<string, number | null>;
    change_2024_vs_2022?: number | null;
    matched_nights?: number | null;
    matched_nights_warmer?: number | null;
    matched_nights_cooler?: number | null;
  };
  analysis_geography?: {
    median_change_2024_vs_2022?: number | null;
  };
  source?: string;
  method?: string;
};

export type ObservedInstantRow = {
  instant_id?: string;
  date?: string;
  local_time?: string;
  temperature_c?: number | null;
  coverage?: { label?: string; valid_zone_count?: number; expected_zone_count?: number };
  activity_id?: string | null;
  observation_status?: string;
  label?: string;
};

export type ObservedSequenceView = {
  unpublished?: boolean;
  not_signal_a?: boolean;
  date_context?: string;
  area?: { area_id?: string; geoid?: string };
  observations?: ObservedInstantRow[];
  direct_differences?: Array<{
    from_instant_id?: string;
    to_instant_id?: string;
    delta_c?: number | null;
    label?: string;
  }>;
  method_note?: string;
  not_claims?: string[];
};

export type PresentedMatched = {
  status: SectionStatus;
  reason: string | null;
  years: Array<{ year: string; meanC: number }>;
  change2024vs2022: number | null;
  medianChange: number | null;
  nightsWarmer: number | null;
  nightsTotal: number | null;
};

export type PresentedInstant = {
  instantId: string;
  label: string;
  date: string;
  localTime: string;
  temperatureC: number;
  activityId: string | null;
};

export type PresentedSequence = {
  status: SectionStatus;
  reason: string | null;
  instants: PresentedInstant[];
  differences: Array<{ fromId: string; toId: string; deltaC: number }>;
};
