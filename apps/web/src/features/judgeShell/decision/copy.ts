/** Public temporal-story copy. No JJA, climate, HeatDose, AfterHeat, or recovery. */

export const MATCHED_TITLE = "MATCHED NIGHTTIME CONDITIONS ACROSS YEARS";
export const MATCHED_WINDOW_LABEL = "MATCHED SUMMER NIGHTTIME WINDOW";
export const MATCHED_DISCLOSURE = "30 Jun-30 Jul, 03:00 local. Same calendar dates. Same hour.";
export const MATCHED_METHOD = "Matched same-calendar dates / same local hour.";
export const MATCHED_NOT_CLIMATE = "This is not a climate trend.";

export const INSTANTS_TITLE = "OBSERVED THERMAL INSTANTS";
export const INSTANTS_SUBTITLE = "Four observations. Not an hourly series.";
export const INSTANTS_DATE = "2024-07-08, America/Phoenix";
export const INSTANTS_GAP = "Gap not observed";
export const INSTANTS_DIFF_LABEL = "Temperature difference between observed instants";

export const STATUS_AVAILABLE = "AVAILABLE";
export const STATUS_INSUFFICIENT = "INSUFFICIENT";
export const STATUS_UNKNOWN = "UNKNOWN";

export const SELECT_AREA = "Select an analysis area on the map.";
export const MISSING_FIELD = "This field is withheld. Missing is not treated as safe.";

export const VERIFY_TITLE = "WHAT SHOULD BE VERIFIED BEFORE ACTION?";
export const VERIFY_MATURITY = "ACTIVE DEVELOPMENT & VALIDATION";
export const COOLSEAL_LINE =
  "CoolSeal: insufficient evidence for this window. Timing is outside the matched 03:00 nighttime window.";
export const COOL_CORRIDORS_LINE =
  "Cool Corridors: real event, inside HVA geography. Thermal verification: INSUFFICIENT EVIDENCE. Public effect claim: NO.";
export const VERIFY_NOT_EFFECT = "Not an intervention effect. Not a treatment result.";

export const FORBIDDEN_STORY_TOKENS = [
  "JJA",
  "climate trend",
  "HeatDose",
  "AfterHeat",
  "cooling rate",
  "24-hour profile",
  "hourly series",
  "recovery",
] as const;
