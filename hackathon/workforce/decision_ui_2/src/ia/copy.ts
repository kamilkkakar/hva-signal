/** Static copy. Explains once. Dynamic fields tell the story. */

export const PRODUCT = "HVA-Signal";
export const PRODUCT_EXPANSION = "Heat, Vulnerability & Action Signal";
export const LAB = "3K Labs";
export const SURFACE = "Decision";

export const AREA_EXPLAIN_ONCE =
  "HVA-Signal divides the selected geography into 25 consistent analysis areas so thermal conditions can be compared across place and time.";

export const GEOID_SECONDARY =
  "Census tract GEOID is a secondary identifier. It is not the primary label.";

export const NOT_LIVE = "Dated window. Not live.";
export const NOT_CURRENT = "Selected time. Not a live now reading.";

export const TEMPORAL_PENDING =
  "Awaiting temporal program. No series is shown until a real contract binds.";

export const MAGNITUDE_PENDING = "Not published";
export const COMPARED_PENDING = "Baseline not bound";
export const COVERAGE_PENDING = "Coverage not bound";
export const INTERPRET_PENDING = "No interpretation until a measured series exists.";
export const DIRECTION_PENDING = "Continue monitoring. Do not rank from an unbound reading.";

export const CHART_SOURCE_PENDING = "Temporal program — contract pending";
export const CHART_PERIOD_PENDING = "Period not bound";
export const CHART_BASELINE_PENDING = "Baseline not bound";
export const CHART_COVERAGE_PENDING = "Coverage not bound";
export const CHART_UNIT_TEMPERATURE = "°C";

export const LEDGER_WHAT = "What happened";
export const LEDGER_RELATIVE = "Relative to";
export const LEDGER_PERIOD = "Period";
export const LEDGER_WHY = "Why it matters";
export const LEDGER_DIRECTION = "Direction";

export const LEDGER_PENDING_WHAT = "No measured change is published yet.";
export const LEDGER_PENDING_RELATIVE = "Baseline not bound.";
export const LEDGER_PENDING_PERIOD = "Period not bound.";
export const LEDGER_PENDING_WHY =
  "Unbound series cannot support a thermal distinction.";
export const LEDGER_PENDING_DIRECTION = "Continue monitoring.";

export const ACTION_EVIDENCE_PENDING =
  "No temporal series is bound on this surface.";
export const ACTION_WHY_PENDING =
  "A missing series is not a safety clearance.";
export const ACTION_DIRECTION_MONITOR = "Continue monitoring.";
export const ACTION_DIRECTION_NO_RANK = "Do not use thermal ranking alone.";
export const ACTION_DIRECTION_COMPARE = "Compare across prior summers when series bind.";
export const ACTION_DIRECTION_VULN = "Review vulnerability context.";
export const ACTION_DIRECTION_COVERAGE = "Verify intervention coverage.";
export const ACTION_VERIFY_BIND = "Confirm the temporal contract and coverage stamp.";
export const ACTION_VERIFY_AREA = "Confirm the selected analysis area and dated window.";
export const ACTION_VERIFY_CONTEXT = "Read local operational constraints before acting.";
export const ACTION_NOT_PROBABILITY = "Not a chance of harm.";
export const ACTION_NOT_EFFICACY = "Not a claim that a treatment worked.";
export const ACTION_NOT_SCORE = "Not a vulnerability score.";
export const ACTION_NOT_DEPLOY = "Does not authorize automatic deployment.";
export const ACTION_NOT_WBGT = "Wet-bulb globe temperature is not shown.";
export const ACTION_NOT_LIVE = "Not a live now reading.";

export const INTERVENTION_TREATED = "Treated analysis areas";
export const INTERVENTION_COMPARISON = "Comparison analysis areas";
export const INTERVENTION_NO_EFFICACY =
  "This chart compares series when bound. It does not establish that a treatment worked.";
export const INTERVENTION_STAMP = "Not a treatment result";

export const VULN_NOT_SCORED = "Vulnerability is context. It is not scored here.";
export const VULN_FACTORS = [
  {
    id: "age",
    label: "Age structure",
    meaning: "Whether nearby residents include groups that typically need more cooling support.",
  },
  {
    id: "housing",
    label: "Housing and shade",
    meaning: "Whether building and canopy conditions may limit indoor and outdoor relief.",
  },
  {
    id: "work",
    label: "Outdoor work",
    meaning: "Whether daytime outdoor labor is common in or next to the analysis area.",
  },
  {
    id: "services",
    label: "Cooling access",
    meaning: "Whether cooling sites, transit, and power reliability are known locally.",
  },
] as const;

export const METHOD_WHY =
  "A single map fill is not a decision. Each question names a comparison so a reviewer can see what was measured, against what, and over which window.";
export const METHOD_HOW =
  "Twenty-five analysis areas stay fixed so place and time can be compared. Temporal series appear only after the temporal program publishes a contract.";
export const METHOD_EVIDENCE =
  "Public numbers require unit, period, baseline, coverage, and source. Missing fields stay empty. Missing is not treated as safe.";

export const SELECTED_NONE = "No analysis area selected. Click the map.";
export const SELECTED_HINT = "Click an analysis area. Charts follow the selection.";

export const MAP_OUTLINE_ONLY = "Outlines only. Fills wait for a bound layer.";
export const MAP_CLICK = "Selection updates every supporting chart.";

export const COMPARISON_PICK = "Select a second analysis area to compare when series bind.";

export const FORBIDDEN_PUBLIC = [
  "q_A",
  "Decision 8",
  "D8",
  "S =",
  "FortyGuard",
  "fortyguard",
  "WBGT",
  "HeatDose",
  "AfterHeat",
  "probability",
  "percent chance",
  "low risk",
  "high risk",
  "traffic light",
  "efficacy",
  "intervention worked",
  "current conditions",
  "real-time",
  "realtime",
  "city-wide",
  "citywide",
  "zone feature vector",
  "feature vector",
] as const;

export const STORY_TITLES = {
  selected_window_state: "Selected-time reading",
  place_unusualness: "Unusual for this place",
  daytime_shape: "Daytime change",
  season_behavior: "Seasonal behavior",
  multi_year_direction: "Multi-year direction",
  intervention_change: "After intervention",
  capacity_context: "Capacity context",
  next_direction: "Next direction",
} as const;

export const CHART_TITLES = {
  hourly_curve: "24-hour curve",
  monthly_trend: "Monthly trend",
  seasonal_comparison: "Seasonal comparison",
  year_over_year: "Year-over-year",
  cumulative_anomaly: "Cumulative anomaly",
  persistence: "Persistence",
  treated_vs_comparison: "Treated vs comparison",
} as const;

export const MAP_MODE_TITLES = {
  selected_time: "Selected time",
  daily_profile: "Daily profile summary",
  summer_mean: "Summer mean",
  seasonal_difference: "Seasonal difference",
  year_over_year: "Year-over-year",
  persistence: "Persistence",
  intervention_change: "Intervention change",
  vulnerability_context: "Vulnerability context",
} as const;
