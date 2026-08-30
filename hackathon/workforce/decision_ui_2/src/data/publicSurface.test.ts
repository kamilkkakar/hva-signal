import { describe, expect, it } from "vitest";
import { CHART_KINDS, MAP_MODE_IDS, STORY_CARD_IDS, isPending } from "@/contracts";
import {
  publicAction,
  publicChart,
  publicIntervention,
  publicMapMode,
  publicStoryCard,
  publicVulnerability,
} from "./publicSurface";

describe("public surface", () => {
  it("keeps every story card magnitude pending", () => {
    for (const id of STORY_CARD_IDS) {
      const card = publicStoryCard(id);
      expect(isPending(card.magnitude)).toBe(true);
      expect(card.magnitude.value).toBeNull();
    }
  });

  it("keeps every temporal chart unbound", () => {
    for (const kind of CHART_KINDS) {
      const chart = publicChart(kind);
      if ("points" in chart) {
        expect(isPending(chart.points)).toBe(true);
      } else {
        expect(isPending(chart.groups)).toBe(true);
      }
    }
  });

  it("keeps every map mode fill unbound", () => {
    for (const id of MAP_MODE_IDS) {
      expect(isPending(publicMapMode(id).fill)).toBe(true);
    }
  });

  it("never claims vulnerability scores or treatment success", () => {
    expect(publicVulnerability().scored).toBe(false);
    expect(publicIntervention().efficacyClaim).toBe(false);
    expect(publicAction("evidence-next").doesNotEstablish.length).toBeGreaterThan(3);
  });
});
