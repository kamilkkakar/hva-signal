import type { ContextComparison, PreparednessEvidenceStatus } from "@/features/experience/narrative";

export type StoryAction = {
  id: string;
  label: string;
  whyShown: string;
};

export type ActionEngineInput = {
  comparisons: readonly ContextComparison[];
  preparedness: PreparednessEvidenceStatus;
  spatialSupported: boolean;
  isPhoenix: boolean;
};

function hasKind(comparisons: readonly ContextComparison[], needle: string): ContextComparison | undefined {
  return comparisons.find((c) => c.kind.toLowerCase().includes(needle));
}

/** Deterministic max-3 evidence-linked actions. No efficacy claims. */
export function buildStoryActions(input: ActionEngineInput): StoryAction[] {
  const actions: StoryAction[] = [];
  const canopy = hasKind(input.comparisons, "canopy");
  const older = hasKind(input.comparisons, "older") ?? hasKind(input.comparisons, "pre_1980") ?? hasKind(input.comparisons, "housing");

  if (
    input.preparedness === "NOT_IDENTIFIED_IN_DATASET" ||
    input.preparedness === "UNKNOWN"
  ) {
    actions.push({
      id: "verify-cooling",
      label: "Verify cooling access",
      whyShown:
        "Cooling access is not established by the available inventory.",
    });
  }

  if (
    canopy &&
    canopy.comparisonAllowed &&
    canopy.comparison === "lower"
  ) {
    actions.push({
      id: "review-shade",
      label: "Review shade / built environment",
      whyShown: "Tree canopy is materially below the comparison median.",
    });
  }

  if (
    older &&
    older.comparisonAllowed &&
    older.comparison === "higher"
  ) {
    actions.push({
      id: "check-older-housing",
      label: "Check older housing heat risk factors",
      whyShown: "Older housing share is above the comparison median.",
    });
  }

  if (!input.spatialSupported) {
    actions.push({
      id: "inspect-temporal",
      label: "Inspect temporal evidence",
      whyShown: "Spatial targeting is not supported for this observation.",
    });
  }

  if (!input.isPhoenix) {
    actions.push({
      id: "switch-phoenix",
      label: "Open Phoenix local analysis",
      whyShown: "Full Level-1 spatial analysis is published for Phoenix.",
    });
  }

  actions.push({
    id: "compare-cities",
    label: "Compare across cities",
    whyShown: "Cross-city snapshot stays available for pattern questions.",
  });

  actions.push({
    id: "review-context",
    label: "Review context layers",
    whyShown: "Context layers change without vendor spend and keep zone selection.",
  });

  // Deduplicate by id, cap at 3
  const seen = new Set<string>();
  const out: StoryAction[] = [];
  for (const action of actions) {
    if (seen.has(action.id)) continue;
    seen.add(action.id);
    out.push(action);
    if (out.length >= 3) break;
  }
  return out;
}

export function contextHighlights(
  comparisons: readonly ContextComparison[],
  preparedness: PreparednessEvidenceStatus,
): string[] {
  const lines: string[] = [];
  for (const fact of comparisons) {
    if (!fact.comparisonAllowed) continue;
    if (fact.kind.toLowerCase().includes("canopy") && fact.comparison === "lower") {
      lines.push("Lower canopy than comparison median");
    }
    if (
      (fact.kind.toLowerCase().includes("older") ||
        fact.kind.toLowerCase().includes("housing") ||
        fact.kind.toLowerCase().includes("pre_1980")) &&
      fact.comparison === "higher"
    ) {
      lines.push("Higher share of older housing");
    }
  }
  if (
    preparedness === "NOT_IDENTIFIED_IN_DATASET" ||
    preparedness === "UNKNOWN"
  ) {
    lines.push("Cooling resource not identified in available inventory");
  }
  return lines;
}
