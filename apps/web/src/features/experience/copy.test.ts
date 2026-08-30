import { describe, expect, it } from "vitest";
import {
  FORBIDDEN_FIRST_READ,
  HERO_LINE,
  HERO_SUPPORT,
  HISTORY_WITHHELD,
  MATCHED_NOT_CLIMATE,
  PRODUCT_EXPANSION,
  RANKING_WITHHELD_BODY,
  historicalPositionSentence,
  preparednessLabel,
} from "./copy";

describe("judge experience first-read copy", () => {
  it("leads with the product sentence, not a method headline", () => {
    expect(HERO_LINE).toBe("From thermal observations to defensible urban heat decisions.");
    expect(HERO_SUPPORT).toContain("local context and preparedness");
    expect(PRODUCT_EXPANSION).toBe("Heat, Vulnerability & Action Signal");
  });

  it("turns q_A into a historical-position sentence without printing q_A", () => {
    const sentence = historicalPositionSentence(0.812);
    expect(sentence).toBe(
      "Warmer than approximately 81% of comparable historical 03:00 observations.",
    );
    expect(sentence).not.toContain("q_A");
  });

  it("keeps preparedness public and never says no cooling site", () => {
    expect(preparednessLabel("IDENTIFIED")).toBe("Identified");
    expect(preparednessLabel("NOT_IDENTIFIED_IN_DATASET")).toBe(
      "Not identified in this dataset",
    );
    expect(preparednessLabel("UNKNOWN")).toBe("Unknown");
    expect(preparednessLabel("NOT_IDENTIFIED_IN_DATASET").toLowerCase()).not.toContain(
      "no cooling site",
    );
  });

  it("does not smuggle first-read jargon into product copy", () => {
    const blob = [
      HERO_LINE,
      HERO_SUPPORT,
      HISTORY_WITHHELD,
      MATCHED_NOT_CLIMATE,
      RANKING_WITHHELD_BODY,
      historicalPositionSentence(0.5),
    ]
      .join("\n")
      .toLowerCase();
    for (const token of FORBIDDEN_FIRST_READ) {
      expect(blob).not.toContain(token.toLowerCase());
    }
  });
});
