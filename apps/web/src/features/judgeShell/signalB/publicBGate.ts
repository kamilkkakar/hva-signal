/** Public Signal B stays DISABLED. GATE 1 stands: 0/25 compatible TCM joins. */

export const PUBLIC_SIGNAL_B = false;
export const P1_LANDING_SELECTED_TIME_REQUESTED = false;

export const GATE1_VALID_ZONE_COUNT = 0;
export const GATE1_EXPECTED_ZONE_COUNT = 25;
export const GATE1_REASON_CODE = "SNAPSHOT_UNAVAILABLE" as const;
export const GATE1_TCM_JOINS = "0/25" as const;

/** Names only — this branch does not flip these flags. */
export const HVA_PUBLIC_TWO_SIGNAL_FLAG = "HVA_PUBLIC_TWO_SIGNAL";
export const VITE_SELECTED_TIME_SNAPSHOT_FLAG = "VITE_HVA_SELECTED_TIME_SNAPSHOT";
export const VITE_LIVE_DEMO_CONFIRMATION_FLAG = "VITE_HVA_LIVE_DEMO_CONFIRMATION";
