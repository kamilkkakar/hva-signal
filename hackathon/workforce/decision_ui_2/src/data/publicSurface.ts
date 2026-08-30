/**
 * Public decision surface. Temporal fields are typed and empty.
 * This module must never import fixtures.
 */
import type {
  ActionPanelModel,
  AnalysisArea,
  ChartKind,
  DataStoryCardModel,
  InterventionModel,
  MapModeId,
  MapModeModel,
  ProvenanceModel,
  QuestionId,
  StoryCardId,
  TemporalChartModel,
  VulnerabilityModel,
} from "@/contracts";
import { ANALYSIS_AREA_COUNT, buildAnalysisAreas, pendingTemporal } from "@/contracts";
import {
  ACTION_DIRECTION_COMPARE,
  ACTION_DIRECTION_COVERAGE,
  ACTION_DIRECTION_MONITOR,
  ACTION_DIRECTION_NO_RANK,
  ACTION_DIRECTION_VULN,
  ACTION_EVIDENCE_PENDING,
  ACTION_NOT_DEPLOY,
  ACTION_NOT_EFFICACY,
  ACTION_NOT_LIVE,
  ACTION_NOT_PROBABILITY,
  ACTION_NOT_SCORE,
  ACTION_NOT_WBGT,
  ACTION_VERIFY_AREA,
  ACTION_VERIFY_BIND,
  ACTION_VERIFY_CONTEXT,
  ACTION_WHY_PENDING,
  AREA_EXPLAIN_ONCE,
  CHART_BASELINE_PENDING,
  CHART_COVERAGE_PENDING,
  CHART_PERIOD_PENDING,
  CHART_SOURCE_PENDING,
  CHART_TITLES,
  CHART_UNIT_TEMPERATURE,
  COMPARED_PENDING,
  COVERAGE_PENDING,
  DIRECTION_PENDING,
  INTERPRET_PENDING,
  INTERVENTION_COMPARISON,
  INTERVENTION_NO_EFFICACY,
  INTERVENTION_TREATED,
  MAGNITUDE_PENDING,
  MAP_MODE_TITLES,
  METHOD_EVIDENCE,
  METHOD_HOW,
  METHOD_WHY,
  NOT_CURRENT,
  NOT_LIVE,
  STORY_TITLES,
  TEMPORAL_PENDING,
  VULN_FACTORS,
  VULN_NOT_SCORED,
} from "@/ia/copy";

export const ANALYSIS_AREAS: readonly AnalysisArea[] = buildAnalysisAreas();

const pendingChrome = (title: string) => ({
  title,
  unit: CHART_UNIT_TEMPERATURE,
  period: CHART_PERIOD_PENDING,
  baseline: CHART_BASELINE_PENDING,
  coverage: CHART_COVERAGE_PENDING,
  source: CHART_SOURCE_PENDING,
});

export function publicStoryCard(id: StoryCardId): DataStoryCardModel {
  return {
    id,
    title: STORY_TITLES[id],
    magnitude: pendingTemporal(MAGNITUDE_PENDING),
    comparedWith: pendingTemporal(COMPARED_PENDING),
    coverage: pendingTemporal(COVERAGE_PENDING),
    interpretation: pendingTemporal(INTERPRET_PENDING),
    direction: pendingTemporal(DIRECTION_PENDING),
  };
}

export function publicChart(kind: ChartKind): TemporalChartModel {
  const chrome = pendingChrome(CHART_TITLES[kind]);
  if (kind === "treated_vs_comparison" || kind === "seasonal_comparison") {
    return {
      kind,
      chrome,
      groups: pendingTemporal(TEMPORAL_PENDING),
    };
  }
  return {
    kind,
    chrome,
    points: pendingTemporal(TEMPORAL_PENDING),
  };
}

export function publicMapMode(id: MapModeId): MapModeModel {
  return {
    id,
    title: MAP_MODE_TITLES[id],
    unit: CHART_UNIT_TEMPERATURE,
    period: CHART_PERIOD_PENDING,
    baseline: CHART_BASELINE_PENDING,
    legend: [
      { id: "unbound", label: "Layer not bound", swatch: null },
      { id: "outline", label: "Analysis area outline", swatch: "#10140e" },
      { id: "selected", label: "Selected analysis area", swatch: "#2f8f78" },
    ],
    fill: pendingTemporal(TEMPORAL_PENDING),
  };
}

export function publicAction(questionId: QuestionId): ActionPanelModel {
  const direction = [ACTION_DIRECTION_MONITOR, ACTION_DIRECTION_NO_RANK];
  if (questionId === "month-season" || questionId === "years-direction") {
    direction.push(ACTION_DIRECTION_COMPARE);
  }
  if (questionId === "after-intervention") {
    direction.push(ACTION_DIRECTION_COVERAGE);
  }
  if (questionId === "capacity-to-cope") {
    direction.push(ACTION_DIRECTION_VULN);
  }
  return {
    evidenceShows: [ACTION_EVIDENCE_PENDING],
    whyItMatters: [ACTION_WHY_PENDING],
    direction,
    verifyNext: [ACTION_VERIFY_BIND, ACTION_VERIFY_AREA, ACTION_VERIFY_CONTEXT],
    doesNotEstablish: [
      ACTION_NOT_PROBABILITY,
      ACTION_NOT_EFFICACY,
      ACTION_NOT_SCORE,
      ACTION_NOT_DEPLOY,
      ACTION_NOT_WBGT,
      ACTION_NOT_LIVE,
    ],
  };
}

export function publicIntervention(): InterventionModel {
  return {
    treatedLabel: INTERVENTION_TREATED,
    comparisonLabel: INTERVENTION_COMPARISON,
    coverage: pendingTemporal(COVERAGE_PENDING),
    period: pendingTemporal(CHART_PERIOD_PENDING),
    chart: {
      kind: "treated_vs_comparison",
      chrome: pendingChrome(CHART_TITLES.treated_vs_comparison),
      groups: pendingTemporal(TEMPORAL_PENDING),
    },
    efficacyClaim: false,
  };
}

export function publicVulnerability(): VulnerabilityModel {
  return {
    scored: false,
    factors: VULN_FACTORS,
    areaNotes: pendingTemporal(TEMPORAL_PENDING),
  };
}

export function publicProvenance(): ProvenanceModel {
  return {
    source: NOT_LIVE,
    clock: NOT_CURRENT,
    geography: `${ANALYSIS_AREA_COUNT} analysis areas`,
    items: [
      { id: "why", label: "Why?", detail: METHOD_WHY },
      { id: "method", label: "Method", detail: METHOD_HOW },
      { id: "evidence", label: "Evidence", detail: METHOD_EVIDENCE },
      { id: "areas", label: "Analysis areas", detail: AREA_EXPLAIN_ONCE },
      { id: "efficacy", label: "Intervention", detail: INTERVENTION_NO_EFFICACY },
      { id: "vuln", label: "Vulnerability", detail: VULN_NOT_SCORED },
    ],
  };
}

export const PUBLIC_MAP_MODES: readonly MapModeModel[] = [
  "selected_time",
  "daily_profile",
  "summer_mean",
  "seasonal_difference",
  "year_over_year",
  "persistence",
  "intervention_change",
  "vulnerability_context",
].map((id) => publicMapMode(id as MapModeId));
