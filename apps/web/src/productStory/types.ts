/** Public analysis story. UI consumes these fields, not backend tokens. */

import type { AnalysisResultStub } from "@/api/analysisJobs";
import type { JobStatus } from "@/types";

export const STORY_ZONE_COUNT = 25 as const;
export const STORY_CLOCK = "03:00" as const;

/** Public B / search / geo stay off this translation layer. */
export const PUBLIC_SIGNAL_B_ON_STORY = false;
export const PUBLIC_SEARCH_ON_STORY = false;
export const PUBLIC_GEO_ON_STORY = false;

export type StoryComparisonState =
  | "idle"
  | "awaiting"
  | "failed"
  | "history_unavailable"
  | "comparable"
  | "too_similar"
  | "not_evaluated";

export type StoryMapMode =
  | "idle"
  | "awaiting"
  | "history_unavailable"
  | "order_shown"
  | "order_withheld";

export type StoryZoneStory = {
  mode: StoryMapMode;
  outline_count: number;
  ranked_fill_count: number;
  hover_enabled: boolean;
  empty_selection: string;
  map_meaning: string;
  selected_zone_id: string | null;
  selected_line: string | null;
};

export type StoryEvidenceLineage = {
  recorded: boolean;
  /** Provenance only. Never a primary status. */
  label: string | null;
  placement: "provenance_only";
};

export type StoryTechnicalDetails = {
  evidence_lineage: StoryEvidenceLineage;
  backend: {
    thermal_differentiation_state: string | null;
    ranking_state: "INSUFFICIENT_EVIDENCE" | "READY" | null;
    reference_quality: string | null;
    evidence_graph_state: string | null;
    limitations: readonly string[];
  };
  method_notes: readonly string[];
};

export type AnalysisStoryViewModel = {
  headline: string;
  summary: string;
  comparison_state: StoryComparisonState;
  comparison_explanation: string;
  observation_time: string;
  analysis_area_label: string;
  zone_count: number;
  reference_period_label: string;
  primary_facts: readonly string[];
  what_this_supports: readonly string[];
  what_this_does_not_establish: readonly string[];
  map_mode: StoryMapMode;
  zone_story: StoryZoneStory;
  evidence_source_summary: string;
  technical_details: StoryTechnicalDetails;
};

export type AnalysisStoryInput = {
  status?: JobStatus | null;
  result?: AnalysisResultStub | null;
  areaId?: string | null;
  analysisTime?: string | null;
  dataMode?: string | null;
  selectedZoneId?: string | null;
  selectedOrder?: number | null;
};
