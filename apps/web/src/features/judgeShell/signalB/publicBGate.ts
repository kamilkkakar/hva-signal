/** Public Signal B is cached evidence only. GATE 1 downtown 0/25 stays a negative fixture. */

export const PUBLIC_SIGNAL_B = true;
export const P1_LANDING_SELECTED_TIME_REQUESTED = false;

/** Downtown TCM fixture remain 0/25. Do not rewrite this hold to the cached 25/25. */
export const GATE1_VALID_ZONE_COUNT = 0;
export const GATE1_EXPECTED_ZONE_COUNT = 25;
export const GATE1_REASON_CODE = "SNAPSHOT_UNAVAILABLE" as const;
export const GATE1_TCM_JOINS = "0/25" as const;

export const HVA_PUBLIC_TWO_SIGNAL_FLAG = "HVA_PUBLIC_TWO_SIGNAL";
export const VITE_SELECTED_TIME_SNAPSHOT_FLAG = "VITE_HVA_SELECTED_TIME_SNAPSHOT";
export const VITE_LIVE_DEMO_CONFIRMATION_FLAG = "VITE_HVA_LIVE_DEMO_CONFIRMATION";
