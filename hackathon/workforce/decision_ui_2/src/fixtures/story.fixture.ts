/** TEST_ONLY fixture. Not imported by production routes. */
import type { DataStoryCardModel } from "@/contracts";
import { AVAILABILITY } from "@/contracts";
import { TEST_ONLY } from "./TEST_ONLY";

export const TEST_ONLY_STORY_CARD: DataStoryCardModel & { readonly __testOnly: typeof TEST_ONLY } =
  {
    __testOnly: TEST_ONLY,
    id: "season_behavior",
    title: "Summer nighttime change",
    magnitude: {
      availability: AVAILABILITY.READY,
      value: { display: "+0.8", unit: "°C" },
    },
    comparedWith: {
      availability: AVAILABILITY.READY,
      value: "Jun–Aug previous year",
    },
    coverage: {
      availability: AVAILABILITY.READY,
      value: "91 / 92 nights",
    },
    interpretation: {
      availability: AVAILABILITY.READY,
      value: "Nighttime conditions were warmer across the selected summer period.",
    },
    direction: {
      availability: AVAILABILITY.READY,
      value: "Review alongside persistence and vulnerability context.",
    },
  };
