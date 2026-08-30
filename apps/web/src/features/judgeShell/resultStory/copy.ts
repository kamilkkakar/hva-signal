/** Primary result story. Public language only. Deep IDs stay with RESCUE-I. */
import { PUBLIC_STATUS } from "@/features/publicLanguage";

export const STORY_KICKER = "Result";
export const STORY_ARIA = "What this analysis found";

export const CONTEXT_ZONES_LABEL = "Zones";
export const CONTEXT_ZONES = "25 zones";
export const CONTEXT_CLOCK_LABEL = "Clock";
export const CONTEXT_CLOCK = "03:00 local";
export const CONTEXT_HISTORY_LABEL = "Comparison";
export const CONTEXT_HISTORY = "Historical comparison 2022–2024";

export const SUPPORTS_LABEL = "What this supports";
export const DOES_NOT_LABEL = "What this does not establish";
export const HOW_SUMMARY = "How this was determined";

export const HOW_HISTORY = "Historical comparison: 2022–2024 at 03:00";
export const HOW_DIFF_SUPPORTED = "Spatial differentiation: Supported — zones may be compared";
export const HOW_DIFF_WITHHELD = "Spatial differentiation: Withheld — zones stay unranked";
export const HOW_DIFF_UNEVALUATED = "Spatial differentiation: Not evaluated";
export const HOW_SEPARATION_LABEL = "Observed separation";
export const HOW_FLOOR_LABEL = "Minimum separation required";

export const STAMP_SUPPORTED = PUBLIC_STATUS.SPATIAL_ORDERING_SUPPORTED;
export const STAMP_WITHHELD = PUBLIC_STATUS.SPATIAL_ORDERING_WITHHELD;
export const STAMP_NOT_EVALUATED = "ORDERING NOT EVALUATED";
export const STAMP_AWAITING = "AWAITING ANALYSIS";
export const STAMP_FAILED = "ANALYSIS DID NOT COMPLETE";

export const SUFFICIENT_HEADLINE =
  "Spatial differences are clear enough to compare";
export const SUFFICIENT_SUMMARY =
  "At 03:00, the historical nighttime pattern across this 25-zone analysis area shows enough separation to display a relative thermal ordering.";
export const SUFFICIENT_SUPPORTS =
  "Thermal ordering can be used as one input when deciding where closer attention or contextual assessment may be needed.";
export const SUFFICIENT_DOES_NOT =
  "Not a probability of harm. Not a severity classification. Not a validated intervention recommendation. Vulnerability, preparedness, operational constraints, and local context remain necessary. This does not authorize automatic deployment of resources.";

export const INSUFFICIENT_HEADLINE =
  "Nighttime patterns are too similar to rank defensibly";
export const INSUFFICIENT_SUMMARY =
  "At 03:00, the historical nighttime pattern across this 25-zone analysis area does not show enough separation to display a relative thermal ordering. Zones stay unranked.";
export const INSUFFICIENT_SUPPORTS =
  "Use other evidence or collect additional thermal observations before making a thermal-priority distinction. Do not use thermal ranking alone for zone prioritization.";
export const INSUFFICIENT_DOES_NOT =
  "An unranked night is still a completed reading. It is not an all-clear and does not mean zones have equal need.";

export const AWAITING_HEADLINE = "No nighttime order is shown yet";
export const AWAITING_SUMMARY =
  "Submit a dated 03:00 replay of this 25-zone analysis area to see whether the historical pattern can be compared.";
export const AWAITING_SUPPORTS = "No thermal-priority distinction is available yet.";
export const AWAITING_DOES_NOT =
  "A missing comparison is not treated as safe and does not mean zones have equal need.";

export const NOT_EVALUATED_HEADLINE = "Historical comparison is not prepared";
export const NOT_EVALUATED_SUMMARY =
  "A relative thermal ordering was not evaluated for this result. Geography ready is not history ready.";
export const NOT_EVALUATED_SUPPORTS =
  "Do not use thermal ranking. Missing evaluation is not treated as safe.";
export const NOT_EVALUATED_DOES_NOT =
  "This does not mean zones have equal need. Vulnerability, preparedness, operational constraints, and local context remain necessary.";

export const FAILED_HEADLINE = "This analysis did not complete";
export const FAILED_SUMMARY =
  "A relative thermal ordering is not shown. Missing output is not treated as safe.";
export const FAILED_SUPPORTS = "Do not use thermal ranking from this run.";
export const FAILED_DOES_NOT =
  "This does not mean zones have equal need and is not an all-clear.";

export const FORBIDDEN_STORY_CHROME = [
  "q_A",
  "Decision 8",
  "D8",
  "FULL_REFERENCE",
  "GRAPH-POPULATED",
  "GRAPH_POPULATED",
  "GRAPH_ABSENT",
  "GRAPH_EMPTY",
  "AWAITING_RESULT",
  "INTERVENTION PRIORITY",
  "INSUFFICIENT_EVIDENCE",
  "INSUFFICIENT EVIDENCE",
  "THERMAL_SPATIAL_DIFFERENTIATION",
  "PHX_NORMALIZED_HAZARD",
  "US_CENSUS_TIGERLINE",
  "TOP3_BOTTOM3",
  "HeatDose",
  "WBGT",
  "FortyGuard",
] as const;

export function publishedStoryCopy(): string[] {
  return [
    STORY_KICKER,
    CONTEXT_ZONES,
    CONTEXT_CLOCK,
    CONTEXT_HISTORY,
    SUPPORTS_LABEL,
    DOES_NOT_LABEL,
    HOW_SUMMARY,
    HOW_HISTORY,
    HOW_DIFF_SUPPORTED,
    HOW_DIFF_WITHHELD,
    HOW_DIFF_UNEVALUATED,
    STAMP_SUPPORTED,
    STAMP_WITHHELD,
    STAMP_NOT_EVALUATED,
    STAMP_AWAITING,
    STAMP_FAILED,
    SUFFICIENT_HEADLINE,
    SUFFICIENT_SUMMARY,
    SUFFICIENT_SUPPORTS,
    SUFFICIENT_DOES_NOT,
    INSUFFICIENT_HEADLINE,
    INSUFFICIENT_SUMMARY,
    INSUFFICIENT_SUPPORTS,
    INSUFFICIENT_DOES_NOT,
    AWAITING_HEADLINE,
    AWAITING_SUMMARY,
    AWAITING_SUPPORTS,
    AWAITING_DOES_NOT,
    NOT_EVALUATED_HEADLINE,
    NOT_EVALUATED_SUMMARY,
    NOT_EVALUATED_SUPPORTS,
    NOT_EVALUATED_DOES_NOT,
    FAILED_HEADLINE,
    FAILED_SUMMARY,
    FAILED_SUPPORTS,
    FAILED_DOES_NOT,
  ];
}
