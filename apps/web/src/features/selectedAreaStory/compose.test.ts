import { describe, expect, it } from "vitest";
import { composeSelectedAreaStory, storyPublicBlob } from "./compose";
import { FORBIDDEN_STORY_TOKENS, Q_DIFFERENT, Q_SUPPORT, Q_THERMAL, Q_VERIFY } from "./copy";
import { analysisAreaNumber } from "./identity";
import {
  AREA_1,
  AREA_25,
  MISSING_GEOID,
  contextView,
  documentFor,
  fact,
  sufficientResult,
  withheldResult,
} from "./fixtures";

describe("selected area identity", () => {
  it("numbers catalog GEOIDs from join_audit order, not backend_order", () => {
    expect(analysisAreaNumber(AREA_1)).toBe(1);
    expect(analysisAreaNumber(AREA_25)).toBe(25);
    expect(analysisAreaNumber(MISSING_GEOID)).toBeNull();
  });
});

describe("selected area decision story", () => {
  it("joins A sufficient with context and keeps API thermal UNKNOWN", () => {
    const context = contextView();
    expect(context.thermal_evidence_status).toBe("UNKNOWN");
    const story = composeSelectedAreaStory({
      selectedGeoid: AREA_1,
      result: sufficientResult(),
      context,
      document: documentFor(context),
    });
    expect(story.identity.label).toBe("Analysis Area 1");
    expect(story.questions.thermal.status).toBe("AVAILABLE");
    expect(story.questions.thermal.a.kind).toBe("order_shown");
    expect(story.questions.thermal.a.q_A).toBe(0.812);
    expect(story.questions.thermal.a.decision8).toBe("SUFFICIENT");
    expect(story.questions.thermal.b.wording).toBe("AVAILABLE NOW — CACHED EVIDENCE");
    expect(story.questions.thermal.b.temperatureC).not.toBeNull();
    expect(story.questions.different.facts.length).toBeGreaterThanOrEqual(4);
    expect(story.questions.different.facts[0]?.sentence).toMatch(/plantable ground/);
    expect(story.questions.verify.rules.map((rule) => rule.id)).toContain("R2");
    expect(story.questions.thermal.label).toBe(Q_THERMAL);
    expect(story.questions.different.label).toBe(Q_DIFFERENT);
    expect(story.questions.support.label).toBe(Q_SUPPORT);
    expect(story.questions.verify.label).toBe(Q_VERIFY);
  });

  it("withholds A rank and does not resurrect q_A", () => {
    const context = contextView();
    const story = composeSelectedAreaStory({
      selectedGeoid: AREA_1,
      result: withheldResult(),
      context,
      document: documentFor(context),
    });
    expect(story.questions.thermal.status).toBe("AVAILABLE");
    expect(story.questions.thermal.a.kind).toBe("order_withheld");
    expect(story.questions.thermal.a.q_A).toBeNull();
    expect(story.questions.thermal.a.orderShown).toBe(false);
    expect(story.identity.areaNumber).toBe(1);
    expect(story.questions.verify.rules.map((rule) => rule.id)).toContain("R1");
    expect(story.questions.verify.rules.map((rule) => rule.id)).not.toContain("R2");
    const blob = storyPublicBlob(story);
    expect(blob).not.toMatch(/backend_order/);
    expect(blob).not.toMatch(/0\.812/);
  });

  it("joins cached B with context without high-risk language", () => {
    const context = contextView();
    const story = composeSelectedAreaStory({
      selectedGeoid: AREA_1,
      context,
      document: documentFor(context),
    });
    expect(story.questions.thermal.a.kind).toBe("absent");
    expect(story.questions.thermal.status).toBe("AVAILABLE");
    expect(story.questions.thermal.b.coverage).toBe("25/25");
    expect(story.questions.thermal.b.clock).toBe("2025-07-15 03:00");
    expect(story.questions.thermal.b.timezone).toBe("America/Phoenix");
    expect(storyPublicBlob(story)).not.toMatch(/high-risk|high risk|heat-risk/);
    expect(story.questions.verify.rules.map((rule) => rule.id)).toContain("R3");
  });

  it("does not invent identity or thermal for a missing zone", () => {
    const story = composeSelectedAreaStory({ selectedGeoid: MISSING_GEOID });
    expect(story.identity.inCatalog).toBe(false);
    expect(story.identity.areaNumber).toBeNull();
    expect(story.questions.thermal.status).toBe("UNKNOWN");
    expect(story.questions.thermal.a.hasRealPane).toBe(false);
    expect(story.questions.thermal.b.temperatureC).toBeNull();
    expect(story.questions.verify.rules.map((rule) => rule.id)).toEqual(["R0"]);
  });

  it("shows unreliable MOE quantity without higher/lower", () => {
    const context = contextView({
      context_facts: [
        fact({
          kind: "median_household_income",
          label: "Median household income",
          value: 48000,
          unit: "USD",
          comparison: "lower",
          comparison_allowed: false,
          quality_status: "MOE_UNRELIABLE",
        }),
        fact({
          kind: "share_age_65_plus",
          label: "Residents age 65+",
          value: 0.22,
          unit: "percent of residents",
          comparison_allowed: false,
          quality_status: "MOE_UNRELIABLE",
        }),
      ],
    });
    const story = composeSelectedAreaStory({
      selectedGeoid: AREA_1,
      context,
      document: documentFor(context),
    });
    const income = story.questions.different.facts.find((row) => row.kind === "median_household_income");
    expect(income?.sentence).toMatch(/\$48,000/);
    expect(income?.sentence).not.toMatch(/higher|lower|above|below/i);
    expect(story.questions.different.facts.find((row) => row.kind === "share_age_65_plus")).toBeUndefined();
  });
});

describe("selected area claim red team", () => {
  it("rejects score, risk, cooling-absent, and formula tokens", () => {
    const context = contextView();
    const story = composeSelectedAreaStory({
      selectedGeoid: AREA_1,
      result: sufficientResult(),
      context,
      document: documentFor(context),
    });
    const blob = storyPublicBlob(story);
    for (const token of FORBIDDEN_STORY_TOKENS) {
      expect(blob, token).not.toContain(token);
    }
    expect(blob).not.toMatch(/°c\s*[x×*]\s*canopy|canopy formula/i);
    expect(story.combined_score_authorized).toBe(false);
    expect(story.vulnerability_score_authorized).toBe(false);
    expect(story.questions.support.sentences.join(" ")).not.toMatch(/no cooling site/i);
  });
});
