import type { QuestionDef } from "@/contracts";

export const QUESTIONS: readonly QuestionDef[] = [
  {
    id: "at-this-time",
    index: 1,
    prompt: "What is happening at this time?",
    short: "At this time",
    mapMode: "selected_time",
    storyCardIds: ["selected_window_state"],
    chartIds: ["hourly_curve"],
  },
  {
    id: "unusual-for-place",
    index: 2,
    prompt: "Is this unusual for this place?",
    short: "Unusual for place",
    mapMode: "selected_time",
    storyCardIds: ["place_unusualness"],
    chartIds: ["year_over_year"],
  },
  {
    id: "heat-over-day",
    index: 3,
    prompt: "How did heat change over the day?",
    short: "Over the day",
    mapMode: "daily_profile",
    storyCardIds: ["daytime_shape"],
    chartIds: ["hourly_curve", "persistence"],
  },
  {
    id: "month-season",
    index: 4,
    prompt: "How did this month / season behave?",
    short: "Month / season",
    mapMode: "seasonal_difference",
    storyCardIds: ["season_behavior"],
    chartIds: ["monthly_trend", "seasonal_comparison"],
  },
  {
    id: "years-direction",
    index: 5,
    prompt: "Is this area getting warmer or cooler over years?",
    short: "Over years",
    mapMode: "year_over_year",
    storyCardIds: ["multi_year_direction"],
    chartIds: ["year_over_year", "cumulative_anomaly"],
  },
  {
    id: "after-intervention",
    index: 6,
    prompt: "Did conditions improve after an intervention?",
    short: "After intervention",
    mapMode: "intervention_change",
    storyCardIds: ["intervention_change"],
    chartIds: ["treated_vs_comparison"],
  },
  {
    id: "capacity-to-cope",
    index: 7,
    prompt: "Who / what may have less capacity to cope?",
    short: "Capacity to cope",
    mapMode: "vulnerability_context",
    storyCardIds: ["capacity_context"],
    chartIds: [],
  },
  {
    id: "evidence-next",
    index: 8,
    prompt: "What does the evidence support doing next?",
    short: "What next",
    mapMode: "selected_time",
    storyCardIds: ["next_direction"],
    chartIds: [],
  },
] as const;

export function questionById(id: QuestionDef["id"]): QuestionDef {
  const found = QUESTIONS.find((question) => question.id === id);
  if (!found) {
    throw new Error(`Unknown question: ${id}`);
  }
  return found;
}
