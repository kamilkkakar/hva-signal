/** Action Intelligence v0 — Decision 8 framing only. Not efficacy. */

export const ACTION_V0_STATUS = "AVAILABLE NOW — DECISION FRAMING" as const;

export const ACTION_V0_SCOPE =
  "Decision framing only. Not an intervention recommendation.";

export const ACTION_V0_TITLE = "What this evidence supports" as const;

export const ACTION_BAND_KICKER = "Action Intelligence" as const;

export const SUPPORTS_COLUMN_LABEL = "Supports" as const;

export const DOES_NOT_COLUMN_LABEL = "Does not establish" as const;

export const REQUIRED_CONTEXT_COPY =
  "Vulnerability, preparedness, operational constraints, and local context remain necessary for actual intervention decisions.";

export const SUFFICIENT_SAYS_COPY =
  "The thermal field supports spatial ordering under the frozen historical signal protocol.";

export const SUFFICIENT_SUPPORTS_COPY =
  "Thermal evidence may be used as one input when deciding where further attention or contextual assessment is needed.";

export const SUFFICIENT_DOES_NOT_COPY = `This does not authorize automatic deployment of resources. ${REQUIRED_CONTEXT_COPY}`;

export const INSUFFICIENT_SAYS_COPY =
  "The thermal field does not support a defensible spatial ordering.";

export const INSUFFICIENT_SUPPORTS_COPY =
  "Do not use thermal ranking alone for zone prioritization.";

export const INSUFFICIENT_DOES_NOT_COPY = `Withholding a rank is not a safety clearance and does not mean zones have equal need. ${REQUIRED_CONTEXT_COPY}`;

export const NOT_EVALUATED_SAYS_COPY =
  "Thermal spatial ordering was not evaluated for this result.";

export const NOT_EVALUATED_SUPPORTS_COPY =
  "Do not use thermal ranking. Missing evaluation is not treated as safe.";

export const NOT_EVALUATED_DOES_NOT_COPY = REQUIRED_CONTEXT_COPY;

export const AWAITING_SAYS_COPY =
  "Action framing waits for a completed analysis.";

export const AWAITING_SUPPORTS_COPY = "No spatial order is authorized yet.";

export const AWAITING_DOES_NOT_COPY = `Missing data is not treated as safe. ${REQUIRED_CONTEXT_COPY}`;

export const SUFFICIENT_STAMP = "SUPPORTS SPATIAL ORDERING" as const;
export const INSUFFICIENT_STAMP = "DO NOT USE THERMAL RANKING ALONE" as const;
export const NOT_EVALUATED_STAMP = "ORDERING NOT EVALUATED" as const;
export const AWAITING_STAMP = "AWAITING ANALYSIS" as const;

export const FORBIDDEN_ACTION_PHRASES = [
  "efficacy",
  "intervention_evidence",
  "harm reduction",
  "reduces harm",
  "dispatch",
  "deploy automatically",
  "all-clear",
  "all clear",
  "equal priority",
  "priorities are equal",
  "low risk",
  "low-risk",
  "preparedness priority",
  "contextual preparedness",
  "hottest",
  "first to treat",
  "first to deploy",
  "probability",
] as const;

export function publishedActionCopy(): string[] {
  return [
    ACTION_V0_STATUS,
    ACTION_V0_SCOPE,
    ACTION_V0_TITLE,
    ACTION_BAND_KICKER,
    SUPPORTS_COLUMN_LABEL,
    DOES_NOT_COLUMN_LABEL,
    REQUIRED_CONTEXT_COPY,
    SUFFICIENT_SAYS_COPY,
    SUFFICIENT_SUPPORTS_COPY,
    SUFFICIENT_DOES_NOT_COPY,
    INSUFFICIENT_SAYS_COPY,
    INSUFFICIENT_SUPPORTS_COPY,
    INSUFFICIENT_DOES_NOT_COPY,
    NOT_EVALUATED_SAYS_COPY,
    NOT_EVALUATED_SUPPORTS_COPY,
    NOT_EVALUATED_DOES_NOT_COPY,
    AWAITING_SAYS_COPY,
    AWAITING_SUPPORTS_COPY,
    AWAITING_DOES_NOT_COPY,
    SUFFICIENT_STAMP,
    INSUFFICIENT_STAMP,
    NOT_EVALUATED_STAMP,
    AWAITING_STAMP,
  ];
}
