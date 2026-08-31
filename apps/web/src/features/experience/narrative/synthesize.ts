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
      value: `${input.selectedTemperatureC.toFixed(1)} °C`,
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
      value: `${sign}${input.matchedChangeC.toFixed(2)} °C vs 2022`,
    });
  }
  if (input.observedHighC != null) {
    signals.push({
      id: "observed_high",
      label: "Observed high",
      value: `${input.observedHighC.toFixed(1)} °C${
        input.observedHighLabel ? ` at ${input.observedHighLabel}` : ""
      }`,
    });
  }
  if (input.preparedness === "NOT_IDENTIFIED_IN_DATASET") {
    signals.push({
      id: "prep",
      label: "Preparedness",
      value: "No heat-relief site identified in available inventory",
    });
  } else if (input.preparedness === "IDENTIFIED") {
    signals.push({
      id: "prep",
      label: "Preparedness",
      value: "Heat-relief site identified in available inventory",
    });
  }
  return signals.slice(0, 5);
}

function buildShows(input: NarrativeSynthesisInput, pattern: NarrativeSynthesis["dominantPattern"]): string[] {
  const lines: string[] = [];
  const area = areaNoun(input);
  const geo = geographyNoun(input);

  if (pattern === "TEMPORAL_CHANGE_DOMINATES" || pattern === "SPATIAL_DIFFERENTIATION_LIMITED") {
    lines.push("Temporal change is the stronger signal.");
  } else if (pattern === "SPATIAL_DIFFERENTIATION_PRESENT") {
    lines.push("Spatial differentiation is meaningful for this observation.");
  } else if (pattern === "INSUFFICIENT_EVIDENCE") {
    lines.push("Thermal evidence is insufficient to support a primary ranking or change claim.");
  }

  if (input.matchedChangeC != null) {
    lines.push(
      `The 2024 matched-nighttime mean was ${formatDeltaPhrase(input.matchedChangeC)} than in 2022 for ${area.toLowerCase()}.`,
    );
  }
  if (input.spatialDiff === "INSUFFICIENT") {
    lines.push(
      `At the selected observation, thermal differences across the ${geo} are too small to support a defensible spatial ranking.`,
    );
  } else if (input.spatialDiff === "SUFFICIENT") {
    lines.push(
      `Thermal differences across the ${geo} are large enough to support a spatial comparison for this observation.`,
    );
  }
  if (input.selectedTemperatureC != null && input.observationStamp) {
    lines.push(
      `${area} was ${input.selectedTemperatureC.toFixed(1)} °C at the selected observation (${input.observationStamp}).`,
    );
  }
  for (const fact of input.contextComparisons.slice(0, 2)) {
    if (fact.comparisonAllowed && fact.comparison) {
      const side =
        fact.comparison === "higher"
          ? "above"
          : fact.comparison === "lower"
            ? "below"
            : "similar to";
      lines.push(`${fact.label} is ${side} the analysis-geography median (${fact.valueDisplay}).`);
    }
  }
  if (input.preparedness === "NOT_IDENTIFIED_IN_DATASET") {
    lines.push("No heat-relief site is identified in the available inventory.");
  } else if (input.preparedness === "IDENTIFIED") {
    lines.push("A heat-relief site is identified in the available inventory.");
  }
  return lines.filter(Boolean);
}

function buildMatters(input: NarrativeSynthesisInput, pattern: NarrativeSynthesis["dominantPattern"]): string[] {
  const lines: string[] = [];
  if (pattern === "TEMPORAL_CHANGE_DOMINATES" || pattern === "SPATIAL_DIFFERENTIATION_LIMITED") {
    lines.push('This is not primarily a "hottest neighborhood" case.');
    lines.push(
      "The stronger evidence is change over time rather than large spatial separation at the selected observation.",
    );
  } else if (pattern === "SPATIAL_DIFFERENTIATION_PRESENT") {
    lines.push(
      "Where conditions differ across analysis areas is a legitimate part of this case — use it with absolute °C and local context.",
    );
  } else if (pattern === "INSUFFICIENT_EVIDENCE") {
    lines.push("Do not manufacture a thermal priority from incomplete evidence.");
  }
  if (matchedMovedWithGeography(input.matchedChangeC, input.geographyMedianChangeC)) {
    lines.push("The selected area moved broadly with the wider analysis geography.");
  }
  for (const fact of input.contextComparisons) {
    if (fact.interpretation) {
      lines.push(fact.interpretation);
      break;
    }
  }
  if (input.preparedness === "NOT_IDENTIFIED_IN_DATASET") {
    lines.push("Cooling access remains something to verify locally.");
  } else if (input.preparedness === "IDENTIFIED") {
    lines.push("Inventory identification is not proof of open, reachable cooling — confirm on the ground.");
  }
  return lines;
}

function buildVerify(input: NarrativeSynthesisInput, pattern: NarrativeSynthesis["dominantPattern"]): string[] {
  const lines: string[] = [];
  if (input.preparedness === "NOT_IDENTIFIED_IN_DATASET" || input.preparedness === "UNKNOWN") {
    lines.push("Verify on-the-ground cooling access.");
  } else if (input.preparedness === "IDENTIFIED") {
    lines.push("Confirm hours, capacity, and reach for the identified heat-relief resource.");
  }
  lines.push(
    "Review local shade and built-environment conditions alongside operational knowledge.",
  );
  if (pattern === "TEMPORAL_CHANGE_DOMINATES" || pattern === "SPATIAL_DIFFERENTIATION_LIMITED") {
    lines.push(
      "Gather additional thermal evidence before using spatial ordering for prioritization.",
    );
  } else if (pattern === "SPATIAL_DIFFERENTIATION_PRESENT") {
    lines.push(
      "Cross-check spatial comparison with absolute °C, matched-window change, and preparedness evidence.",
    );
  } else if (pattern === "INSUFFICIENT_EVIDENCE") {
    lines.push("Identify which missing thermal or preparedness evidence would unlock a defensible next step.");
  }
  return lines;
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
