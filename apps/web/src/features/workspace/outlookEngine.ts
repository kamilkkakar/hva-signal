import type { ObservationMode } from "./types";

export type OutlookLiveState = "idle" | "running" | "ready" | "error";
export type OutlookSpatialState = "supported" | "withheld" | "not_evaluated";

export type OutlookStep = {
  id: string;
  label: string;
  whyShown: string;
};

export type OutlookPlan = {
  state: "needs_observation" | "observing" | "evidence_limited" | "ready";
  summary: string;
  steps: OutlookStep[];
  basis: string;
};

export type OutlookEngineInput = {
  cityLabel: string;
  observationMode: ObservationMode;
  liveState: OutlookLiveState;
  spatialState: OutlookSpatialState;
  hasHistoricalMatchedEvidence: boolean;
  observedInstantCount: number;
};

function addStep(target: OutlookStep[], step: OutlookStep): void {
  if (!target.some((candidate) => candidate.id === step.id)) {
    target.push(step);
  }
}

/**
 * Deterministic next-evidence planner.
 *
 * This does not forecast, rank, or estimate intervention efficacy. It only
 * chooses the next supported observation/comparison from evidence that the
 * product already exposes.
 */
export function buildOutlookPlan(input: OutlookEngineInput): OutlookPlan {
  const steps: OutlookStep[] = [];

  if (input.observationMode === "live" && input.liveState === "running") {
    addStep(steps, {
      id: "finish-current-observation",
      label: "Finish the selected-time observation",
      whyShown:
        "A bounded request is already running; keep the published field visible until it returns.",
    });
  } else if (input.observationMode === "live" && input.liveState === "error") {
    addStep(steps, {
      id: "recover-live-observation",
      label: "Review and rerun the observation",
      whyShown:
        "The selected-time request did not produce bindable zone evidence; no result was inferred.",
    });
  } else if (input.observationMode === "live" && input.liveState === "idle") {
    addStep(steps, {
      id: "run-selected-time-observation",
      label: "Run a selected-time observation",
      whyShown:
        `No Live thermal field is active for ${input.cityLabel}; the published observation remains the evidence baseline.`,
    });
  }

  if (input.spatialState === "withheld") {
    addStep(steps, {
      id: "add-temporal-evidence",
      label: "Add another observed time",
      whyShown:
        "The current field is too similar across zones, so another real observation is more useful than stretching it into a ranking.",
    });
  } else if (input.spatialState === "supported") {
    addStep(steps, {
      id: "test-pattern-persistence",
      label: "Recheck the pattern at another hour",
      whyShown:
        "The current ordering is supported for this observation; another observed hour can show whether it persists.",
    });
  } else if (input.observationMode !== "live" || input.liveState === "ready") {
    addStep(steps, {
      id: "compare-observed-time",
      label: "Compare another observed time",
      whyShown:
        "A selected-time snapshot is descriptive; an additional measured instant adds temporal context without implying a forecast.",
    });
  }

  if (input.observationMode === "live" && input.liveState === "ready") {
    addStep(steps, {
      id: "compare-published-observation",
      label: "Compare with the published observation",
      whyShown:
        "The active Live result and the published snapshot are separate measured instants for the same city geography.",
    });
  }

  if (input.hasHistoricalMatchedEvidence) {
    addStep(steps, {
      id: "review-matched-history",
      label: "Review matched nighttime history",
      whyShown:
        "Phoenix has a validated same-hour historical reference that is kept separate from selected-time absolute temperature.",
    });
  } else if (input.observedInstantCount >= 2) {
    addStep(steps, {
      id: "review-observed-instants",
      label: "Review observed thermal instants",
      whyShown:
        `${input.observedInstantCount} discrete observations are available; conditions between them were not measured.`,
    });
  }

  addStep(steps, {
    id: "compare-city-snapshot",
    label: "Compare the four-city snapshot",
    whyShown:
      "The published city observations share one absolute temperature scale and remain descriptive rather than predictive.",
  });

  const planSteps = steps.slice(0, 3);
  if (input.observationMode === "live" && input.liveState === "running") {
    return {
      state: "observing",
      summary: "Complete the observation before changing the claim",
      steps: planSteps,
      basis: "Active bounded request + currently published evidence",
    };
  }
  if (input.observationMode === "live" && input.liveState !== "ready") {
    return {
      state: "needs_observation",
      summary: "Establish the next observed thermal field",
      steps: planSteps,
      basis: "Selected city + observation state + available evidence",
    };
  }
  if (input.spatialState === "withheld" || input.spatialState === "not_evaluated") {
    return {
      state: "evidence_limited",
      summary: "Add time before adding certainty",
      steps: planSteps,
      basis: "Active observation + spatial-evidence state + published capabilities",
    };
  }
  return {
    state: "ready",
    summary: "Test whether the supported pattern persists",
    steps: planSteps,
    basis: "Active observation + spatial-evidence state + published capabilities",
  };
}
