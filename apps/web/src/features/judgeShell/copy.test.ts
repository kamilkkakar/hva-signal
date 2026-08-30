import { describe, expect, it } from "vitest";
import {
  CHIP_CLOCK,
  CHIP_SOURCE,
  CHIP_WINDOW,
  CHIP_WINDOW_ID,
  DOES_NOT_BULLETS,
  FORBIDDEN_FIRST_PAINT,
  HERO_LINE,
  PRODUCT_EXPANSION,
  publishedJudgeCopy,
} from "./copy";

describe("judge shell first-paint copy", () => {
  const published = publishedJudgeCopy().join("\n");
  const lower = published.toLowerCase();

  it("locks UX-A V1 hero and HVA expansion", () => {
    expect(HERO_LINE).toBe(
      "Shows a nighttime heat order only when the thermal field can defend it.",
    );
    expect(PRODUCT_EXPANSION).toBe("Heat, Vulnerability & Action Signal");
  });

  it("names phoenix-demo, 25-zone window, 03:00, replay", () => {
    expect(CHIP_WINDOW_ID).toBe("phoenix-demo");
    expect(CHIP_WINDOW).toBe("25-zone window");
    expect(CHIP_CLOCK).toBe("03:00");
    expect(CHIP_SOURCE).toBe("replay");
    expect(published).toContain("phoenix-demo");
    expect(published).toContain("25-zone window");
    expect(published).toContain("03:00");
    expect(published).toContain("replay");
  });

  it("forbids city-wide, real-time, vendor, copilot, and login claims", () => {
    for (const phrase of FORBIDDEN_FIRST_PAINT) {
      expect(lower).not.toContain(phrase);
    }
    expect(lower).not.toContain("probability");
    expect(lower).not.toContain("fortyguard");
  });

  it("keeps forecast and overnight only as does-not nouns", () => {
    const doesNot = DOES_NOT_BULLETS.join(" ").toLowerCase();
    expect(doesNot).toContain("forecast");
    expect(doesNot).toContain("overnight");
    const withoutDoesNot = publishedJudgeCopy()
      .filter((line) => !DOES_NOT_BULLETS.includes(line as (typeof DOES_NOT_BULLETS)[number]))
      .join("\n")
      .toLowerCase();
    expect(withoutDoesNot).not.toContain("forecast");
    expect(withoutDoesNot).not.toContain("overnight");
    expect(withoutDoesNot).not.toContain("scenario");
  });
});
