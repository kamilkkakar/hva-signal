/** Question-first information architecture. */

export const QUESTION_IDS = [
  "at-this-time",
  "unusual-for-place",
  "heat-over-day",
  "month-season",
  "years-direction",
  "after-intervention",
  "capacity-to-cope",
  "evidence-next",
] as const;

export type QuestionId = (typeof QUESTION_IDS)[number];

export type QuestionDef = {
  readonly id: QuestionId;
  readonly index: number;
  readonly prompt: string;
  readonly short: string;
  readonly mapMode: MapModeId;
  readonly storyCardIds: readonly StoryCardId[];
  readonly chartIds: readonly ChartKind[];
};

export const MAP_MODE_IDS = [
  "selected_time",
  "daily_profile",
  "summer_mean",
  "seasonal_difference",
  "year_over_year",
  "persistence",
  "intervention_change",
  "vulnerability_context",
] as const;

export type MapModeId = (typeof MAP_MODE_IDS)[number];

export const STORY_CARD_IDS = [
  "selected_window_state",
  "place_unusualness",
  "daytime_shape",
  "season_behavior",
  "multi_year_direction",
  "intervention_change",
  "capacity_context",
  "next_direction",
] as const;

export type StoryCardId = (typeof STORY_CARD_IDS)[number];

export const CHART_KINDS = [
  "hourly_curve",
  "monthly_trend",
  "seasonal_comparison",
  "year_over_year",
  "cumulative_anomaly",
  "persistence",
  "treated_vs_comparison",
] as const;

export type ChartKind = (typeof CHART_KINDS)[number];
