import type { AnalysisResultStub } from "@/api/analysisJobs";
import type { JobStatus } from "@/types";
import { evidenceGraphPresentation } from "@/utils/evidencePresentation";
import { shouldContinuePolling } from "@/utils/jobPolling";
import {
  INSUFFICIENT_REFERENCE,
  THERMAL_SPATIAL_DIFFERENTIATION_INSUFFICIENT,
  rankingPresentation,
} from "@/utils/mapLayer";
import {
  CLOCK_FACT,
  COMPARISON_SUFFICIENT,
  COMPARISON_TOO_SIMILAR,
  DOES_NOT_CLEARANCE,
  DOES_NOT_COMBINED,
  DOES_NOT_CONTEXT,
  DOES_NOT_DEPLOY,
  DOES_NOT_LIVE,
  DOES_NOT_MISSING_SAFE,
  DOES_NOT_VULNERABILITY,
  EVIDENCE_LINEAGE_RECORDED,
  EXPLANATION_AWAITING,
  EXPLANATION_FAILED,
  EXPLANATION_HISTORY,
  EXPLANATION_IDLE,
  EXPLANATION_NOT_EVALUATED,
  HEADLINE_AWAITING,
  HEADLINE_COMPARABLE,
  HEADLINE_FAILED,
  HEADLINE_HISTORY,
  HEADLINE_IDLE,
  HEADLINE_NOT_EVALUATED,
  HEADLINE_TOO_SIMILAR,
  HISTORY_FACT,
  MAP_MEANING_AWAITING,
  MAP_MEANING_HISTORY,
  MAP_MEANING_IDLE,
  MAP_MEANING_SHOWN,
  MAP_MEANING_WITHHELD,
  METHOD_D8,
  METHOD_QA,
  METHOD_S,
  ORDER_FACT,
  REFERENCE_AVAILABLE,
  REFERENCE_NOT_PREPARED,
  REFERENCE_NOT_STATED,
  SNAPSHOT_OFF_FACT,
  SOURCE_FACT,
  SOURCE_SUMMARY,
  SUMMARY_AWAITING,
  SUMMARY_COMPARABLE,
  SUMMARY_FAILED,
  SUMMARY_HISTORY,
  SUMMARY_IDLE,
  SUMMARY_NOT_EVALUATED,
  SUMMARY_TOO_SIMILAR,
  SUPPORTS_AWAITING,
  SUPPORTS_COMPARABLE,
  SUPPORTS_FAILED,
  SUPPORTS_HISTORY,
  SUPPORTS_IDLE,
  SUPPORTS_NOT_EVALUATED,
  SUPPORTS_TOO_SIMILAR,
  WINDOW_FACT,
  WITHHOLD_FACT,
  ZONE_EMPTY,
  formatAreaLabel,
  formatObservationTime,
  formatOrderHover,
  formatReferenceYears,
} from "./copy";
import {
  STORY_ZONE_COUNT,
  type AnalysisStoryInput,
  type AnalysisStoryViewModel,
  type StoryComparisonState,
  type StoryMapMode,
  type StoryTechnicalDetails,
  type StoryZoneStory,
} from "./types";

function limitationList(result: AnalysisResultStub | null | undefined): string[] {
  if (result?.system_limitations?.length) {
    return [...result.system_limitations];
  }
  return result?.limitations ? [...result.limitations] : [];
}

function differentiationState(
  result: AnalysisResultStub | null | undefined,
): string | null {
  return (
    result?.thermal_differentiation_state ??
    result?.hazard_spread?.differentiation_state ??
    null
  );
}

function referenceQuality(
  result: AnalysisResultStub | null | undefined,
): string | null {
  return (
    result?.reference_quality ??
    result?.hazard_spread?.reference_quality ??
    null
  );
}

function orderingPermitted(
  result: AnalysisResultStub | null | undefined,
): boolean {
  const zones = result?.zones ?? [];
  if (zones.length === 0) {
    return false;
  }
  return zones.every((zone) => zone.thermal_ordering_permitted === true);
}

function resolveComparisonState(input: AnalysisStoryInput): StoryComparisonState {
  const status = input.status ?? null;
  const result = input.result ?? null;
  const limitations = limitationList(result);

  if (status === "failed" || status === "unknown_job") {
    return "failed";
  }
  if (status != null && shouldContinuePolling(status)) {
    return "awaiting";
  }
  if (status == null) {
    return "idle";
  }
  if (status !== "complete" && status !== "partial") {
    return "not_evaluated";
  }
  if (result == null) {
    return "not_evaluated";
  }
  if (limitations.includes(INSUFFICIENT_REFERENCE)) {
    return "history_unavailable";
  }

  const state = differentiationState(result)?.toUpperCase() ?? null;
  const ranking = rankingPresentation(result.zones);

  if (state === "INSUFFICIENT") {
    return "too_similar";
  }
  if (state === "SUFFICIENT" && orderingPermitted(result)) {
    return "comparable";
  }
  if (state === "SUFFICIENT") {
    return "not_evaluated";
  }
  if (
    ranking.state === "INSUFFICIENT_EVIDENCE" &&
    (limitations.includes(THERMAL_SPATIAL_DIFFERENTIATION_INSUFFICIENT) ||
      status === "complete" ||
      status === "partial")
  ) {
    return "too_similar";
  }
  return "not_evaluated";
}

function mapModeFor(state: StoryComparisonState): StoryMapMode {
  switch (state) {
    case "comparable":
      return "order_shown";
    case "too_similar":
      return "order_withheld";
    case "history_unavailable":
      return "history_unavailable";
    case "awaiting":
      return "awaiting";
    default:
      return "idle";
  }
}

function geographyReady(state: StoryComparisonState): boolean {
  return (
    state === "comparable" ||
    state === "too_similar" ||
    state === "history_unavailable" ||
    state === "failed"
  );
}

function headlineFor(state: StoryComparisonState): string {
  switch (state) {
    case "comparable":
      return HEADLINE_COMPARABLE;
    case "too_similar":
      return HEADLINE_TOO_SIMILAR;
    case "history_unavailable":
      return HEADLINE_HISTORY;
    case "awaiting":
      return HEADLINE_AWAITING;
    case "failed":
      return HEADLINE_FAILED;
    case "not_evaluated":
      return HEADLINE_NOT_EVALUATED;
    default:
      return HEADLINE_IDLE;
  }
}

function summaryFor(state: StoryComparisonState): string {
  switch (state) {
    case "comparable":
      return SUMMARY_COMPARABLE;
    case "too_similar":
      return SUMMARY_TOO_SIMILAR;
    case "history_unavailable":
      return SUMMARY_HISTORY;
    case "awaiting":
      return SUMMARY_AWAITING;
    case "failed":
      return SUMMARY_FAILED;
    case "not_evaluated":
      return SUMMARY_NOT_EVALUATED;
    default:
      return SUMMARY_IDLE;
  }
}

function explanationFor(state: StoryComparisonState): string {
  switch (state) {
    case "comparable":
      return COMPARISON_SUFFICIENT;
    case "too_similar":
      return COMPARISON_TOO_SIMILAR;
    case "history_unavailable":
      return EXPLANATION_HISTORY;
    case "awaiting":
      return EXPLANATION_AWAITING;
    case "failed":
      return EXPLANATION_FAILED;
    case "not_evaluated":
      return EXPLANATION_NOT_EVALUATED;
    default:
      return EXPLANATION_IDLE;
  }
}

function supportsFor(state: StoryComparisonState): readonly string[] {
  switch (state) {
    case "comparable":
      return [COMPARISON_SUFFICIENT, SUPPORTS_COMPARABLE];
    case "too_similar":
      return [COMPARISON_TOO_SIMILAR, SUPPORTS_TOO_SIMILAR];
    case "history_unavailable":
      return [SUPPORTS_HISTORY];
    case "awaiting":
      return [SUPPORTS_AWAITING];
    case "failed":
      return [SUPPORTS_FAILED];
    case "not_evaluated":
      return [SUPPORTS_NOT_EVALUATED];
    default:
      return [SUPPORTS_IDLE];
  }
}

function doesNotFor(state: StoryComparisonState): readonly string[] {
  if (state === "awaiting" || state === "idle") {
    return [DOES_NOT_MISSING_SAFE, DOES_NOT_CONTEXT];
  }
  return [
    DOES_NOT_DEPLOY,
    DOES_NOT_VULNERABILITY,
    DOES_NOT_COMBINED,
    DOES_NOT_LIVE,
    DOES_NOT_CLEARANCE,
    DOES_NOT_CONTEXT,
  ];
}

function primaryFactsFor(state: StoryComparisonState): readonly string[] {
  const facts = [CLOCK_FACT, WINDOW_FACT, SOURCE_FACT, SNAPSHOT_OFF_FACT];
  if (state === "comparable") {
    return [...facts, ORDER_FACT];
  }
  if (state === "too_similar") {
    return [...facts, WITHHOLD_FACT];
  }
  if (state === "history_unavailable") {
    return [...facts, HISTORY_FACT];
  }
  return facts;
}

function mapMeaningFor(mode: StoryMapMode): string {
  switch (mode) {
    case "order_shown":
      return MAP_MEANING_SHOWN;
    case "order_withheld":
      return MAP_MEANING_WITHHELD;
    case "history_unavailable":
      return MAP_MEANING_HISTORY;
    case "awaiting":
      return MAP_MEANING_AWAITING;
    default:
      return MAP_MEANING_IDLE;
  }
}

function zoneStoryFor(
  state: StoryComparisonState,
  input: AnalysisStoryInput,
): StoryZoneStory {
  const mode = mapModeFor(state);
  const ready = geographyReady(state);
  const shown = state === "comparable";
  const selectedLine =
    shown && input.selectedZoneId != null && input.selectedOrder != null
      ? formatOrderHover(input.selectedZoneId, input.selectedOrder)
      : null;

  return {
    mode,
    outline_count: ready ? STORY_ZONE_COUNT : 0,
    ranked_fill_count: shown ? STORY_ZONE_COUNT : 0,
    hover_enabled: shown,
    empty_selection: ZONE_EMPTY,
    map_meaning: mapMeaningFor(mode),
    selected_zone_id: selectedLine ? input.selectedZoneId ?? null : null,
    selected_line: selectedLine,
  };
}

function referencePeriodLabel(
  state: StoryComparisonState,
  result: AnalysisResultStub | null | undefined,
): string {
  const quality = referenceQuality(result);
  const years = formatReferenceYears(result?.hazard_spread?.historical_years);

  if (state === "history_unavailable" || quality === "INSUFFICIENT_REFERENCE") {
    return REFERENCE_NOT_PREPARED;
  }
  if (quality === "FULL_REFERENCE") {
    return years ? `${REFERENCE_AVAILABLE} · ${years}` : REFERENCE_AVAILABLE;
  }
  if (years) {
    return years;
  }
  return REFERENCE_NOT_STATED;
}

function technicalDetails(
  result: AnalysisResultStub | null | undefined,
): StoryTechnicalDetails {
  const graph = evidenceGraphPresentation(result);
  const recorded = graph.state === "GRAPH_POPULATED";
  const ranking = result ? rankingPresentation(result.zones) : null;

  return {
    evidence_lineage: {
      recorded,
      label: recorded ? EVIDENCE_LINEAGE_RECORDED : null,
      placement: "provenance_only",
    },
    backend: {
      thermal_differentiation_state: differentiationState(result),
      ranking_state: ranking?.state ?? null,
      reference_quality: referenceQuality(result),
      evidence_graph_state: result == null ? null : graph.state,
      limitations: limitationList(result),
    },
    method_notes: [METHOD_QA, METHOD_D8, METHOD_S],
  };
}

/** Translate existing job facts. Does not compute q_A, Decision 8, or S. */
export function presentAnalysisStory(
  input: AnalysisStoryInput = {},
): AnalysisStoryViewModel {
  const state = resolveComparisonState(input);
  const mapMode = mapModeFor(state);

  return {
    headline: headlineFor(state),
    summary: summaryFor(state),
    comparison_state: state,
    comparison_explanation: explanationFor(state),
    observation_time: formatObservationTime(input.analysisTime),
    analysis_area_label: formatAreaLabel(input.areaId),
    zone_count: STORY_ZONE_COUNT,
    reference_period_label: referencePeriodLabel(state, input.result),
    primary_facts: primaryFactsFor(state),
    what_this_supports: supportsFor(state),
    what_this_does_not_establish: doesNotFor(state),
    map_mode: mapMode,
    zone_story: zoneStoryFor(state, input),
    evidence_source_summary: SOURCE_SUMMARY,
    technical_details: technicalDetails(input.result),
  };
}

export function storyFromJob(input: {
  status?: JobStatus | null;
  result?: AnalysisResultStub | null;
  areaId?: string | null;
  analysisTime?: string | null;
  dataMode?: string | null;
  selectedZoneId?: string | null;
  selectedOrder?: number | null;
}): AnalysisStoryViewModel {
  return presentAnalysisStory(input);
}

export function storyPublicChrome(view: AnalysisStoryViewModel): string[] {
  return [
    view.headline,
    view.summary,
    view.comparison_state,
    view.comparison_explanation,
    view.observation_time,
    view.analysis_area_label,
    String(view.zone_count),
    view.reference_period_label,
    ...view.primary_facts,
    ...view.what_this_supports,
    ...view.what_this_does_not_establish,
    view.map_mode,
    view.zone_story.mode,
    view.zone_story.empty_selection,
    view.zone_story.map_meaning,
    view.zone_story.selected_line ?? "",
    view.evidence_source_summary,
  ];
}
