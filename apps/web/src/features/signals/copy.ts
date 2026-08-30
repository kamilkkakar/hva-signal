/** Frozen-candidate copy. B1/B3 stay human-open. Never stamp FROZEN. */

export const NO_COMBINED_SCORE_COPY =
  "Signal A and Signal B stay independent. A combined score is not authorized.";

export const REUSE_ONLY_COPY =
  "Signal B is reuse-only. A compatible cached or replay snapshot may be shown. This interface does not request live acquisition or spend.";

export const REFERENCE_NOT_PREPARED_COPY =
  "Historical reference is not prepared. Signal A, Decision 8, and thermal ranking are unavailable. Missing reference is not treated as safe.";

export const REFERENCE_NOT_PREPARED_ACQUISITION_COPY =
  "Signal A (historically normalized nighttime thermal, q_A / Decision 8) is not prepared for this analysis window. Selecting a place does not start historical reference acquisition.";

export const REFERENCE_NOT_PREPARED_LOCK_COPY =
  "Signal A stays unavailable until a separate historical reference package exists. Geography ready is not historical ready. This is not a safety clearance.";

export const SIGNAL_A_INERT_COPY =
  "Signal A is inert until a 25-zone analysis geography is ready. Geography ready is not historical ready.";

export const SIGNAL_A_PENDING_COPY =
  "Signal A is pending only if a historical reference package already exists. National analysis windows stay not prepared.";

export const SIGNAL_A_READY_COPY =
  "Signal A is a historically normalized nighttime thermal claim (q_A / Decision 8) for this analysis window. It is not Signal B and not a combined score.";

export const SIGNAL_A_INSUFFICIENT_COPY =
  "Signal A does not support a thermal ranking. Insufficient evidence is not treated as low risk or as a safety clearance.";

export const SIGNAL_A_FAILED_COPY =
  "Signal A failed closed. This does not hide Signal B and is not a safety clearance.";

export const B_NOT_REQUESTED_COPY =
  "Signal B is not requested until a 25-zone analysis geography is ready.";

export const B_CACHED_COPY =
  "Signal B is showing a reusable selected-time snapshot. This is cached or replay evidence, not a live acquisition.";

export const B_UNAVAILABLE_COPY =
  "Signal B has no compatible snapshot for this analysis window. Missing data is not treated as cool or safe.";

export const B_FETCHING_COPY =
  "Signal B is fetching a selected-time snapshot for the 25-zone analysis window. This interface does not call a vendor.";

export const B_PARTIAL_COPY =
  "Signal B is partial. Zones without a value are unknown. Partial coverage is not filled, ranked, or colored as complete.";

export const B_READY_COPY =
  "Signal B has a selected-time snapshot for the 25-zone analysis window. Values are absolute °C. This is not q_A, rank, or Decision 8.";

export const LIVE_DEMO_TITLE = "Generate a live thermal snapshot?";
export const LIVE_DEMO_BODY =
  "This future confirmation would ask HVA-Signal to attempt a hosted demo snapshot. The server decides whether that request may run. This interface does not authorize spend and does not send a vendor call.";
export const LIVE_DEMO_PRIMARY = "Run live demo";
export const LIVE_DEMO_SECONDARY = "Continue without live snapshot";

export const REFERENCE_NOT_PREPARED_STAMP = "REFERENCE NOT PREPARED";

export const FORBIDDEN_L6_PHRASES = [
  "preparedness priority",
  "contextual preparedness",
  "low risk",
  "low-risk",
  "analysis succeeded",
  "analysis complete",
] as const;

export const FORBIDDEN_AUTH_PHRASES = [
  "log in",
  "login",
  "sign up",
  "signup",
  "create account",
  "my account",
  "persona",
] as const;

export const FORBIDDEN_SPEND_PHRASES = [
  "allowance_remaining",
  "remaining units",
  "authorized_max_units",
  "demo_budget",
  "approve spend",
  "authorize spend",
  "enter api key",
] as const;

export const FORBIDDEN_COMBINED_PHRASES = [
  "combined score:",
  "blended score",
  "composite heat",
] as const;

export const FORBIDDEN_LIVE_CHROME = [
  "fortyguard live",
  "data_mode=live",
  "operational (0–12h)",
] as const;

export function publishedSignalCopy(): string[] {
  return [
    NO_COMBINED_SCORE_COPY,
    REUSE_ONLY_COPY,
    REFERENCE_NOT_PREPARED_COPY,
    REFERENCE_NOT_PREPARED_ACQUISITION_COPY,
    REFERENCE_NOT_PREPARED_LOCK_COPY,
    SIGNAL_A_INERT_COPY,
    SIGNAL_A_PENDING_COPY,
    SIGNAL_A_READY_COPY,
    SIGNAL_A_INSUFFICIENT_COPY,
    SIGNAL_A_FAILED_COPY,
    B_NOT_REQUESTED_COPY,
    B_CACHED_COPY,
    B_UNAVAILABLE_COPY,
    B_FETCHING_COPY,
    B_PARTIAL_COPY,
    B_READY_COPY,
    REFERENCE_NOT_PREPARED_STAMP,
  ];
}
