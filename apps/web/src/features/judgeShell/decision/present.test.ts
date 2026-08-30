import { describe, expect, it } from "vitest";
import { formatDeltaC, presentMatched, presentObserved } from "./present";
import { PRODUCT_QUESTIONS } from "./questions";

const SEED = "04013107401";

const matchedDoc = {
  window_label: "MATCHED SUMMER NIGHTTIME WINDOW",
  selected_area: {
    geoid: SEED,
    mean_by_year: { "2022": 32.8, "2023": 33.81, "2024": 34.33 },
    change_2024_vs_2022: 1.54,
    matched_nights: 31,
    matched_nights_warmer: 22,
    matched_nights_cooler: 9,
  },
  analysis_geography: { median_change_2024_vs_2022: 1.53 },
};

const observedDoc = {
  observations: [
    { instant_id: "03:00_D", date: "2024-07-08", local_time: "03:00", temperature_c: 34.5196234375, label: "03:00 D" },
    { instant_id: "15:00", date: "2024-07-08", local_time: "15:00", temperature_c: 42.32812109375, label: "15:00", activity_id: "92086c4c-1550-4263-8ac8-9a6c9e030bc4" },
    { instant_id: "21:00", date: "2024-07-08", local_time: "21:00", temperature_c: 39.25628125, label: "21:00", activity_id: "9865bd33-43a0-42b0-bc9b-74b27510002d" },
    { instant_id: "03:00_D+1", date: "2024-07-09", local_time: "03:00", temperature_c: 34.67551328125, label: "03:00 D+1" },
  ],
  direct_differences: [
    { from_instant_id: "03:00_D", to_instant_id: "15:00", delta_c: 7.8084976562499975 },
    { from_instant_id: "15:00", to_instant_id: "21:00", delta_c: -3.0718398437499985 },
    { from_instant_id: "21:00", to_instant_id: "03:00_D+1", delta_c: -4.580767968750003 },
  ],
};

describe("temporal story presenters", () => {
  it("fails closed without a selected analysis area", () => {
    expect(presentMatched(null, matchedDoc, null).status).toBe("UNKNOWN");
    expect(presentObserved(null, observedDoc, null).status).toBe("UNKNOWN");
  });

  it("presents matched-window facts from a real compact view", () => {
    const view = presentMatched(SEED, matchedDoc, null);
    expect(view.status).toBe("AVAILABLE");
    expect(view.years).toHaveLength(3);
    expect(view.change2024vs2022).toBeCloseTo(1.54, 2);
    expect(view.medianChange).toBeCloseTo(1.53, 2);
    expect(view.nightsWarmer).toBe(22);
    expect(view.nightsTotal).toBe(31);
    expect(formatDeltaC(view.change2024vs2022 ?? 0)).toBe("+1.54 C");
  });

  it("orders four observed instants and keeps 15:00/21:00 activity ids", () => {
    const view = presentObserved(SEED, observedDoc, null);
    expect(view.status).toBe("AVAILABLE");
    expect(view.instants.map((item) => item.instantId)).toEqual([
      "03:00_D",
      "15:00",
      "21:00",
      "03:00_D+1",
    ]);
    expect(view.instants[1]?.activityId).toBe("92086c4c-1550-4263-8ac8-9a6c9e030bc4");
    expect(view.instants[2]?.activityId).toBe("9865bd33-43a0-42b0-bc9b-74b27510002d");
    expect(view.differences).toHaveLength(3);
  });

  it("withholds a section when a required field is missing", () => {
    const broken = { ...matchedDoc, selected_area: { ...matchedDoc.selected_area, change_2024_vs_2022: null } };
    expect(presentMatched(SEED, broken, null).status).toBe("INSUFFICIENT");
  });
});

describe("product questions and claim contract", () => {
  it("ships the seven Prompt-15 questions", () => {
    expect(PRODUCT_QUESTIONS.map((item) => item.index)).toEqual([1, 2, 3, 4, 5, 6, 7]);
    expect(PRODUCT_QUESTIONS[2]?.prompt.toLowerCase()).toContain("matched nighttime");
    expect(PRODUCT_QUESTIONS[3]?.prompt.toLowerCase()).toContain("observed times");
  });

  it("keeps forbidden longitudinal tokens out of public story titles", async () => {
    const copy = await import("./copy");
    const narrative = [
      copy.MATCHED_TITLE,
      copy.MATCHED_DISCLOSURE,
      copy.INSTANTS_TITLE,
      copy.INSTANTS_SUBTITLE,
      copy.VERIFY_TITLE,
      copy.COOLSEAL_LINE,
      copy.COOL_CORRIDORS_LINE,
    ].join(" ").toLowerCase();
    expect(narrative).not.toContain("jja");
    expect(narrative).not.toContain("climate trend");
    expect(narrative).not.toContain("cooling rate");
    expect(narrative).not.toContain("24-hour profile");
    expect(narrative).not.toContain("heatdose");
    expect(narrative).not.toContain("afterheat");
    expect(copy.FORBIDDEN_STORY_TOKENS).toEqual(expect.arrayContaining(["JJA", "HeatDose"]));
  });
});
