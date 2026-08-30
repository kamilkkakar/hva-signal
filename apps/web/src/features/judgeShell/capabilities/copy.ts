/** Frozen Wave 2 capability-expansion copy. Statuses are not gauges. */

export const CAPABILITY_KICKER = "Active capability expansion" as const;

export const CAPABILITY_TITLE = "Beyond a snapshot" as const;

export const CAPABILITY_LEAD =
  "Development ledger only — not live product modes you can switch. Shown when data, definition, interpretation, and validation are defensible.";

export const CAPABILITY_SPINE = [
  "OBSERVE",
  "CONTEXTUALIZE",
  "EXPOSURE",
  "STRESS",
  "ANTICIPATE",
  "ACT",
] as const;

export const BAND_ON_THIS_SURFACE = "On this surface" as const;
export const BAND_NEXT_GATED = "Next / gated" as const;
export const BAND_IN_DEVELOPMENT = "In development" as const;

export const SIGNAL_A_NAME = "Nighttime Historical Thermal Signal" as const;
export const SIGNAL_A_MATURITY = "AVAILABLE NOW" as const;
export const SIGNAL_A_QUESTION =
  "How unusual was each zone at 3 a.m. versus its own historical nights?";
export const SIGNAL_A_SCOPE =
  "phoenix-demo replay at 03:00. Not live. Not a city search.";

export const ACTION_NAME = "Action Intelligence" as const;
export const ACTION_MATURITY = "AVAILABLE NOW — DECISION FRAMING" as const;
export const ACTION_QUESTION =
  "What does the thermal evidence authorize or withhold?";
export const ACTION_SCOPE =
  "Decision 8 translate only. Not an intervention recommendation.";

export const SIGNAL_B_NAME = "Selected-Time Thermal Snapshot" as const;
export const SIGNAL_B_MATURITY = "INTEGRATION TESTING" as const;
export const SIGNAL_B_QUESTION =
  "What was each zone’s average temperature, in °C, at the selected hour?";
export const SIGNAL_B_SCOPE =
  "Not on this surface. Code existence is not enablement.";

export const PLACE_SEARCH_NAME = "Place search" as const;
export const PLACE_SEARCH_MATURITY = "DISABLED" as const;
export const PLACE_SEARCH_QUESTION = "Can I look up another city from this surface?";
export const PLACE_SEARCH_SCOPE = "Public place search is off.";

export const GEOGRAPHY_NAME = "Public geography resolve" as const;
export const GEOGRAPHY_MATURITY = "DISABLED" as const;
export const GEOGRAPHY_QUESTION =
  "Does a Census-place resolve publish an analysis window here?";
export const GEOGRAPHY_SCOPE =
  "Resolve is off. phoenix-demo is a frozen analysis window, not municipal coverage.";

export const HOSTED_LIVE_NAME = "Hosted live" as const;
export const HOSTED_LIVE_MATURITY = "DISABLED" as const;
export const HOSTED_LIVE_QUESTION = "Is this thermal evidence live?";
export const HOSTED_LIVE_SCOPE = "Hosted live acquisition is off. This surface is replay.";

export const HEATDOSE_NAME = "HeatDose" as const;
export const HEATDOSE_MATURITY = "ANALYTICAL DEVELOPMENT" as const;
export const HEATDOSE_QUESTION =
  "How did environmental exposure accumulate over a named window?";
export const HEATDOSE_SCOPE = "Not shown. No number. No curve. No gauge.";

export const AFTERHEAT_NAME = "AfterHeat" as const;
export const AFTERHEAT_MATURITY = "ACTIVE DEVELOPMENT & VALIDATION" as const;
export const AFTERHEAT_QUESTION =
  "How does the outdoor thermal field behave after the daytime peak?";
export const AFTERHEAT_SCOPE = "Not shown. No number. Not a recovery score.";

export const WBGT_NAME = "WBGT" as const;
export const WBGT_MATURITY = "INTEGRATION PATHWAY / BLOCKED inputs" as const;
export const WBGT_QUESTION =
  "What is wet-bulb globe temperature for a named form, once complete inputs exist?";
export const WBGT_SCOPE =
  "Not shown. Calculation BLOCKED. Will not approximate from incomplete inputs.";

export const PROBABILITY_NAME = "Calibrated Probability" as const;
export const PROBABILITY_MATURITY = "MODEL DEVELOPMENT, numeric BLOCKED" as const;
export const PROBABILITY_QUESTION =
  "What is the calibrated chance of a defined thermal event within a defined horizon?";
export const PROBABILITY_SCOPE =
  "Not shown. No public numeric probability. Unusualness is not a chance.";

export const HVA_HEAT_LINE =
  "Thermal field on a 25-zone analysis window. That is what we measure.";
export const HVA_VULNERABILITY_LINE =
  "People and places are not equally exposed. We do not score this yet.";
export const HVA_ACTION_LINE =
  "Authorize or withhold a nighttime order. Not a treatment plan.";

export const MODULES_INTRO =
  "Modules move onto the public surface only when data, definition, interpretation, and validation are defensible. HeatDose, AfterHeat, WBGT, and probability have no public number.";

export const HEATDOSE_WHAT =
  "Intended to distinguish a short-lived peak from sustained environmental exposure over a named window — not what a body absorbed.";
export const HEATDOSE_RULE =
  "Research candidate. No frozen definition. No number, curve, or gauge. Not personal burden.";

export const AFTERHEAT_WHAT =
  "Intended to describe persistence and dissipation of the outdoor field after the daytime peak.";
export const AFTERHEAT_RULE =
  "No frozen metric. Not a recovery score. The nighttime historical signal is not AfterHeat.";

export const WBGT_WHAT =
  "A future wet-bulb globe temperature reading for a named form, at that source’s resolution, once complete meteorological inputs exist.";
export const WBGT_RULE =
  "Calculation BLOCKED. Will not approximate WBGT from temperature alone or from incomplete inputs. No number.";

export const PROBABILITY_WHAT =
  "A future calibrated chance of a clearly defined thermal event within a defined horizon, after validation.";
export const PROBABILITY_RULE =
  "Public numeric probability is BLOCKED. Historical unusualness is not a probability. No percent.";

export const SIGNAL_A_WHAT =
  "How unusual was each zone at 3 a.m. compared with its own historical 3 a.m., and is the difference large enough to show an order?";
export const SIGNAL_A_RULE =
  "A withheld order means the night was too flat to defend a ranking. That is a feature, not a failure. Missing data is not treated as safe.";

export const ACTION_WHAT =
  "Translates Decision 8 into authorize or withhold. Vulnerability, preparedness, operational constraints, and local context remain necessary for actual intervention decisions.";
export const ACTION_RULE =
  "Not a treatment plan. Not proof a project worked. Not automatic deploy.";

export const SIGNAL_B_WHAT =
  "A selected-hour zone temperature snapshot, in °C. Description only. Not unusualness. Not an order.";
export const SIGNAL_B_RULE =
  "INTEGRATION TESTING. Not AVAILABLE NOW. No fabricated temperature.";

export const PLACE_SEARCH_WHAT =
  "Type a place name and resolve an analysis window.";
export const PLACE_SEARCH_RULE =
  "DISABLED. Geography available is not thermal evidence available.";

export const GEOGRAPHY_WHAT =
  "Public geography resolve for a Census place.";
export const GEOGRAPHY_RULE =
  "DISABLED. phoenix-demo is a frozen 25-zone analysis window, not municipal coverage.";

export const HOSTED_LIVE_WHAT = "Hosted live thermal acquisition.";
export const HOSTED_LIVE_RULE = "DISABLED. This surface is historical replay.";

export const NOT_THIS_PRODUCT = [
  "Combined A+B score",
  "Vulnerability or preparedness scores",
  "Certified cooling or intervention proof",
  "Public percent or harm probability",
] as const;

export const FORBIDDEN_CAPABILITY_PHRASES = [
  "future features",
  "coming someday",
  "roadmap only",
  "city-wide",
  "the city",
  "overnight recovery",
  "failed recovery",
  "safe-dose",
  "personal dose",
  "occupational",
  "harm reduction",
  "efficacy",
  "dispatch",
  "hottest",
  "intervention priority",
  "preparedness priority",
  "fortyguard",
  "remaining units",
  "current conditions",
  "real-time",
] as const;

export const FAKE_TIMELINE_LABELS = [
  "Current",
  "Forecast",
  "Scenario",
  "Overnight",
] as const;

export function publishedCapabilityCopy(): string[] {
  return [
    CAPABILITY_KICKER,
    CAPABILITY_TITLE,
    CAPABILITY_LEAD,
    ...CAPABILITY_SPINE,
    BAND_ON_THIS_SURFACE,
    BAND_NEXT_GATED,
    BAND_IN_DEVELOPMENT,
    SIGNAL_A_NAME,
    SIGNAL_A_MATURITY,
    SIGNAL_A_QUESTION,
    SIGNAL_A_SCOPE,
    SIGNAL_A_WHAT,
    SIGNAL_A_RULE,
    ACTION_NAME,
    ACTION_MATURITY,
    ACTION_QUESTION,
    ACTION_SCOPE,
    ACTION_WHAT,
    ACTION_RULE,
    SIGNAL_B_NAME,
    SIGNAL_B_MATURITY,
    SIGNAL_B_QUESTION,
    SIGNAL_B_SCOPE,
    SIGNAL_B_WHAT,
    SIGNAL_B_RULE,
    PLACE_SEARCH_NAME,
    PLACE_SEARCH_MATURITY,
    PLACE_SEARCH_QUESTION,
    PLACE_SEARCH_SCOPE,
    PLACE_SEARCH_WHAT,
    PLACE_SEARCH_RULE,
    GEOGRAPHY_NAME,
    GEOGRAPHY_MATURITY,
    GEOGRAPHY_QUESTION,
    GEOGRAPHY_SCOPE,
    GEOGRAPHY_WHAT,
    GEOGRAPHY_RULE,
    HOSTED_LIVE_NAME,
    HOSTED_LIVE_MATURITY,
    HOSTED_LIVE_QUESTION,
    HOSTED_LIVE_SCOPE,
    HOSTED_LIVE_WHAT,
    HOSTED_LIVE_RULE,
    HEATDOSE_NAME,
    HEATDOSE_MATURITY,
    HEATDOSE_QUESTION,
    HEATDOSE_SCOPE,
    HEATDOSE_WHAT,
    HEATDOSE_RULE,
    AFTERHEAT_NAME,
    AFTERHEAT_MATURITY,
    AFTERHEAT_QUESTION,
    AFTERHEAT_SCOPE,
    AFTERHEAT_WHAT,
    AFTERHEAT_RULE,
    WBGT_NAME,
    WBGT_MATURITY,
    WBGT_QUESTION,
    WBGT_SCOPE,
    WBGT_WHAT,
    WBGT_RULE,
    PROBABILITY_NAME,
    PROBABILITY_MATURITY,
    PROBABILITY_QUESTION,
    PROBABILITY_SCOPE,
    PROBABILITY_WHAT,
    PROBABILITY_RULE,
    HVA_HEAT_LINE,
    HVA_VULNERABILITY_LINE,
    HVA_ACTION_LINE,
    MODULES_INTRO,
    ...NOT_THIS_PRODUCT,
  ];
}

export function unpublishedNumericCopy(): string[] {
  return [
    HEATDOSE_MATURITY,
    HEATDOSE_QUESTION,
    HEATDOSE_SCOPE,
    HEATDOSE_WHAT,
    HEATDOSE_RULE,
    AFTERHEAT_MATURITY,
    AFTERHEAT_QUESTION,
    AFTERHEAT_SCOPE,
    AFTERHEAT_WHAT,
    AFTERHEAT_RULE,
    WBGT_MATURITY,
    WBGT_QUESTION,
    WBGT_SCOPE,
    WBGT_WHAT,
    WBGT_RULE,
    PROBABILITY_MATURITY,
    PROBABILITY_QUESTION,
    PROBABILITY_SCOPE,
    PROBABILITY_WHAT,
    PROBABILITY_RULE,
  ];
}
