import type { AnalysisResultStub, ZoneDecisionStub } from "@/api/analysisJobs";
import type { JobStatus } from "@/types";
import { shouldContinuePolling } from "./jobPolling";
import {
  ARCHITECTURE_THERMAL_DIFF_MESSAGE,
  INSUFFICIENT_REFERENCE,
  THERMAL_SPATIAL_DIFFERENTIATION_INSUFFICIENT,
} from "./mapLayer";

export type EvidenceGraphState =
  | "AWAITING_RESULT"
  | "GRAPH_ABSENT"
  | "GRAPH_EMPTY"
  | "GRAPH_POPULATED";

export type EvidenceGraphPresentation = {
  state: EvidenceGraphState;
  empty: boolean;
  populated: boolean;
  copy: string;
};

export type ProbabilityFieldsPresentation = {
  shown: boolean;
  label: string;
};

export type StallCopy = {
  message: string;
  recoveryHint: string;
};

const PROBABILITY_BLOCKED_LABEL =
  "Blocked — insufficient evidence. Not a probability pending Gate 0.";

function collectionLength(value: unknown): number {
  return Array.isArray(value) ? value.length : 0;
}

export function evidenceGraphPresentation(
  result: AnalysisResultStub | null | undefined,
): EvidenceGraphPresentation {
  if (result == null) {
    return {
      state: "AWAITING_RESULT",
      empty: false,
      populated: false,
      copy: "Evidence graph is not available until the job returns a result.",
    };
  }

  if (!("evidence_graph" in result) || result.evidence_graph == null) {
    return {
      state: "GRAPH_ABSENT",
      empty: false,
      populated: false,
      copy: "Evidence graph was not included in this result.",
    };
  }

  const nodeCount = collectionLength(result.evidence_graph.nodes);
  const edgeCount = collectionLength(result.evidence_graph.edges);
  if (nodeCount === 0 && edgeCount === 0) {
    return {
      state: "GRAPH_EMPTY",
      empty: true,
      populated: false,
      copy: "Evidence graph is empty. Missing data is not treated as safe.",
    };
  }

  return {
    state: "GRAPH_POPULATED",
    empty: false,
    populated: true,
    copy: "Evidence graph has recorded nodes or edges. This does not authorize a spatial thermal claim.",
  };
}

export function probabilityFieldsPresentation(
  zones: ZoneDecisionStub[] | null | undefined,
): ProbabilityFieldsPresentation | null {
  if (!zones?.some((zone) => zone.probability != null)) {
    return null;
  }
  return {
    shown: true,
    label: PROBABILITY_BLOCKED_LABEL,
  };
}

export function decisionThermalLimitation(input: {
  status: JobStatus | null | undefined;
  limitations: readonly string[] | null | undefined;
}): string | null {
  if (input.status !== "complete" && input.status !== "partial") {
    return null;
  }
  if (input.limitations?.includes(INSUFFICIENT_REFERENCE)) {
    return null;
  }
  if (
    !input.limitations?.includes(THERMAL_SPATIAL_DIFFERENTIATION_INSUFFICIENT)
  ) {
    return null;
  }
  return ARCHITECTURE_THERMAL_DIFF_MESSAGE;
}

export type Decision8EvidencePanel = {
  title: string;
  observedSpread: number | null;
  requiredSpread: number | null;
  floorDisplay: string | null;
  statistic: string;
  tailGroupSize: string;
  areaConfigVersion: string | null;
  policyVersion: string;
  referenceVersion: string | null;
  zoneGeometryVersion: string | null;
  historicalYears: number[] | null;
  referenceHour: string | null;
  referenceQuality: string;
  result: string;
  reason: string | null;
};

function formatQaFloorUnits(floor: number | null | undefined): string | null {
  if (floor == null || Number.isNaN(Number(floor))) {
    return null;
  }
  return `${Number(floor).toFixed(2)} q_A units`;
}

export function decision8EvidencePanel(
  result: AnalysisResultStub | null | undefined,
): Decision8EvidencePanel | null {
  const spread = result?.hazard_spread;
  if (!spread) {
    return null;
  }
  const state = spread.differentiation_state;
  if (state !== "INSUFFICIENT" && state !== "SUFFICIENT") {
    return null;
  }
  const top = spread.top_group_size ?? 3;
  const insufficient = state === "INSUFFICIENT";
  return {
    title: insufficient
      ? "THERMAL ORDERING NOT SUPPORTED"
      : "THERMAL SPATIAL DIFFERENTIATION SUFFICIENT",
    observedSpread: spread.observed_spread ?? null,
    requiredSpread: spread.floor ?? 0.1,
    floorDisplay: formatQaFloorUnits(spread.floor ?? 0.1),
    statistic: spread.metric ?? "TOP3_BOTTOM3_MEAN_DIFFERENCE",
    tailGroupSize: `${top} / 25 per tail`,
    areaConfigVersion: result.versions?.area_config_version ?? null,
    policyVersion: spread.policy_version ?? "",
    referenceVersion: spread.reference_version ?? null,
    zoneGeometryVersion: spread.zone_geometry_version ?? null,
    historicalYears: spread.historical_years ?? null,
    referenceHour: spread.reference_hour ?? null,
    referenceQuality: spread.reference_quality ?? "",
    result: insufficient
      ? "THERMAL_SPATIAL_DIFFERENTIATION_INSUFFICIENT"
      : "SUFFICIENT",
    reason: spread.suppression_reason ?? null,
  };
}

export function stallCopy(input: {
  stalled: boolean;
  status: JobStatus | null | undefined;
  hasResult: boolean;
}): StallCopy | null {
  if (!input.stalled) {
    return null;
  }

  const orchestrationGap =
    shouldContinuePolling(input.status ?? null) && !input.hasResult;

  if (orchestrationGap) {
    return {
      message:
        "Job status did not advance. Orchestration is not connected yet. Polling stopped.",
      recoveryHint:
        "The last request is still held. Resubmit after orchestration is connected.",
    };
  }

  return {
    message: "Job status did not advance. Polling stopped.",
    recoveryHint: "The last request is still held. Resubmit to retry.",
  };
}
