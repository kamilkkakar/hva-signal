import {
  formatDeltaPhrase,
  matchedMovedWithGeography,
  PATTERN_COPY,
  resolveDominantPattern,
} from "./pattern";
import type {
  EvidenceSignal,
  NarrativeSynthesis,
  NarrativeSynthesisInput,
} from "./types";

function areaNoun(input: NarrativeSynthesisInput): string {
  return input.areaLabel ?? "This analysis area";
}

function geographyNoun(input: NarrativeSynthesisInput): string {
  const n = input.analysisAreaCount;
  return n > 0 ? `${n}-area analysis geography` : "analysis geography";
}

function buildEvidenceSummary(input: NarrativeSynthesisInput): EvidenceSignal[] {
  const signals: EvidenceSignal[] = [];
  if (input.selectedTemperatureC != null) {
    signals.push({
      id: "selected_obs",
      label: "Selected observation",
      value: `${input.selectedTemperatureC.toFixed(1)}°C`,
    });
  }
  if (input.spatialDiff === "INSUFFICIENT") {
    signals.push({ id: "spatial", label: "Spatial differentiation", value: "Limited" });
  } else if (input.spatialDiff === "SUFFICIENT") {
    signals.push({ id: "spatial", label: "Spatial differentiation", value: "Present" });
  }
  if (input.matchedChangeC != null) {
    const sign = input.matchedChangeC >= 0 ? "+" : "";
    signals.push({
      id: "matched",
      label: "Matched nighttime change",
      value: `${sign}${input.matchedChangeC.toFixed(2)}°C\n2024 vs 2022`,
    });
  }
  if (input.observedHighC != null) {
    signals.push({
      id: "observed_high",
      label: "Highest observed instant",
      value: `${input.observedHighC.toFixed(1)}°C${
        input.observedHighLabel ? `\n${input.observedHighLabel}` : ""
      }`,
    });
  }
  if (input.preparedness === "NOT_IDENTIFIED_IN_DATASET") {
    signals.push({
      id: "prep",
      label: "Heat-relief resources",
      value: "Not identified\nin available inventory",
    });
  } else if (input.preparedness === "IDENTIFIED") {
    signals.push({
      id: "prep",
      label: "Heat-relief resources",
      value: "Identified\nin available inventory",
    });
  }
  return signals.slice(0, 5);
}

function buildShows(input: NarrativeSynthesisInput, pattern: NarrativeSynthesis["dominantPattern"]): string[] {
  const lines: string[] = [];
  const area = areaNoun(input);
  const geo = geographyNoun(input);

  if (pattern === "TEMPORAL_CHANGE_DOMINATES" || pattern === "SPATIAL_DIFFERENTIATION_LIMITED") {
    if (input.matchedChangeC != null) {
      lines.push(
        `Temporal change is the stronger signal. The 2024 matched-window mean was ${formatDeltaPhrase(input.matchedChangeC)} than in 2022.`,
      );
    } else {
      lines.push("Temporal change is the stronger signal.");
    }
  } else if (pattern === "SPATIAL_DIFFERENTIATION_PRESENT") {
    lines.push("Spatial differentiation is meaningful for this observation.");
  } else if (pattern === "INSUFFICIENT_EVIDENCE") {
    lines.push("Thermal evidence is insufficient to support a primary ranking or change claim.");
  } else if (pattern === "PREPAREDNESS_GAP_REQUIRES_VERIFICATION") {
    lines.push("Cooling access verification is the clearest next evidence gap.");
  } else if (pattern === "CONTEXT_WARRANTS_INVESTIGATION") {
    lines.push("Local context is the strongest available signal for this case.");
  }

  if (input.spatialDiff === "INSUFFICIENT") {
    lines.push(
      "Spatial separation is weak at this observation. The thermal field does not support a defensible area ranking.",
    );
  } else if (input.spatialDiff === "SUFFICIENT") {
    lines.push(
      `Thermal differences across the ${geo} support a spatial comparison for this observation.`,
    );
  }

  const canopy = input.contextComparisons.find(
    (fact) =>
      fact.comparisonAllowed &&
      fact.comparison &&
      /canopy|tree/i.test(fact.label) &&
      fact.tone === "weaken",
  );
  if (canopy && input.preparedness === "NOT_IDENTIFIED_IN_DATASET") {
    lines.push(
      "Local context does not point to a simple low-canopy explanation, while no heat-relief site is identified in the available inventory.",
    );
  } else if (canopy && input.preparedness === "IDENTIFIED") {
    lines.push(
      "Local context does not point to a simple low-canopy explanation, and a heat-relief site is identified in the available inventory.",
    );
  } else if (canopy) {
    lines.push(
      "Local context does not point to a simple low-canopy explanation for the selected thermal pattern.",
    );
  } else if (input.preparedness === "NOT_IDENTIFIED_IN_DATASET") {
    lines.push("No heat-relief site is identified in the available inventory.");
  } else if (input.preparedness === "IDENTIFIED") {
    lines.push("A heat-relief site is identified in the available inventory.");
  } else if (input.selectedTemperatureC != null && input.observationStamp && lines.length < 3) {
    lines.push(
      `${area} was ${input.selectedTemperatureC.toFixed(1)} °C at the selected observation (${input.observationStamp}).`,
    );
  }

  return lines.filter(Boolean).slice(0, 3);
}

function buildMatters(input: NarrativeSynthesisInput, pattern: NarrativeSynthesis["dominantPattern"]): string[] {
  const lines: string[] = [];
  if (pattern === "TEMPORAL_CHANGE_DOMINATES" || pattern === "SPATIAL_DIFFERENTIATION_LIMITED") {
    lines.push(
      'The strongest evidence is change over time, not a "hottest neighborhood" signal at the selected observation.',
    );
  } else if (pattern === "SPATIAL_DIFFERENTIATION_PRESENT") {
    lines.push(
      "Where conditions differ across analysis areas is a legitimate part of this case — use it with absolute °C and local context.",
    );
  } else if (pattern === "INSUFFICIENT_EVIDENCE") {
    lines.push("Do not manufacture a thermal priority from incomplete evidence.");
  }
  if (input.preparedness === "NOT_IDENTIFIED_IN_DATASET" || input.preparedness === "UNKNOWN") {
    lines.push("Cooling access remains something to verify locally.");
  } else if (input.preparedness === "IDENTIFIED") {
    lines.push("Inventory identification is not proof of open, reachable cooling — confirm on the ground.");
  }
  if (lines.length < 2) {
    for (const fact of input.contextComparisons) {
      if (fact.interpretation) {
        lines.push(fact.interpretation);
        break;
      }
    }
  }
  if (lines.length < 2 && matchedMovedWithGeography(input.matchedChangeC, input.geographyMedianChangeC)) {
    lines.push("The selected area moved broadly with the wider analysis geography.");
  }
  return lines.slice(0, 3);
}

function buildVerify(input: NarrativeSynthesisInput, pattern: NarrativeSynthesis["dominantPattern"]): string[] {
  const lines: string[] = [];
  if (input.preparedness === "NOT_IDENTIFIED_IN_DATASET" || input.preparedness === "UNKNOWN") {
    lines.push("Verify on-the-ground cooling access.");
  } else if (input.preparedness === "IDENTIFIED") {
    lines.push("Confirm hours, capacity, and reach for the identified heat-relief resource.");
  }
  lines.push("Review local shade / built-environment conditions with operational knowledge.");
  if (pattern === "TEMPORAL_CHANGE_DOMINATES" || pattern === "SPATIAL_DIFFERENTIATION_LIMITED") {
    lines.push("Gather more thermal evidence before using spatial ordering for prioritization.");
  } else if (pattern === "SPATIAL_DIFFERENTIATION_PRESENT") {
    lines.push(
      "Cross-check spatial comparison with absolute °C, matched-window change, and preparedness evidence.",
    );
  } else if (pattern === "INSUFFICIENT_EVIDENCE") {
    lines.push("Identify which missing thermal or preparedness evidence would unlock a defensible next step.");
  }
  return lines.slice(0, 3);
}

export function synthesizeNarrative(input: NarrativeSynthesisInput): NarrativeSynthesis {
  const dominantPattern = resolveDominantPattern(input);
  const copy = PATTERN_COPY[dominantPattern];
  let patternSummary = copy.payAttention;
  if (
    dominantPattern === "TEMPORAL_CHANGE_DOMINATES" &&
    input.matchedChangeC != null &&
    input.spatialDiff === "INSUFFICIENT"
  ) {
    const sign = input.matchedChangeC >= 0 ? "higher" : "lower";
    patternSummary = `Matched nighttime conditions were ${sign} in the 2024 window, while differences across the ${geographyNoun(input)} at the selected observation are too small to support a defensible ranking.`;
  }
  return {
    dominantPattern,
    patternTitle: copy.title,
    patternSummary,
    evidenceSummary: buildEvidenceSummary(input),
    whatEvidenceShows: buildShows(input, dominantPattern),
    whyItMatters: buildMatters(input, dominantPattern),
    verifyNext: buildVerify(input, dominantPattern),
  };
}
