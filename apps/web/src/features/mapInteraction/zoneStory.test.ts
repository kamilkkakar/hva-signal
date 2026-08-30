import { describe, expect, it } from "vitest";
import { historicalCatalog } from "./fixtures";
import { detailFromState, hoverFromState } from "./detail";
import { formatQuantile4 } from "./policy";
import { initialInteractionState, reduceInteraction } from "./state";
import {
  formatObservationLabel,
  positionPct,
  storyFromZone,
} from "./zoneStory";

describe("zone story", () => {
  it("formats an AOI-local observation without 16-decimal q_A", () => {
    expect(formatObservationLabel("2022-06-30T03:00:00")).toBe(
      "30 Jun 2022 · 03:00 local",
    );
    expect(formatQuantile4(0.2294)).toBe("0.2294");
    expect(formatQuantile4(0.2294000000000001)).toBe("0.2294");
    expect(formatQuantile4(Math.PI)).toBe("3.1416");
    expect(formatQuantile4(Math.PI).length).toBeLessThan(8);
  });

  it("builds an authorized zone story with expandable index and relative order", () => {
    const catalog = historicalCatalog(true);
    const zone = catalog.zones[0];
    expect(zone).toBeTruthy();
    if (!zone) {
      return;
    }
    const story = storyFromZone(zone);
    expect(story.position_shown).toBe(true);
    expect(story.position_meaning).toBe(
      "Position within this zone's own 03:00 historical reference.",
    );
    expect(story.observation_label).toBe("15 Jul 2024 · 03:00 local");
    expect(story.source_story).toBe("Replay evidence");
    expect(story.relative_order_line).toBe("Relative order within this analysis — 1 of 5");
    expect(story.q_A_display).toBe("0.2000");
    expect(story.q_A_display).not.toMatch(/\d\.\d{5,}/);
    expect(positionPct(zone.q_A_value)).toBe(20);
  });

  it("suppresses position, order, and q_A when the night is not differentiated", () => {
    const catalog = historicalCatalog(false);
    const zone = catalog.zones[0];
    expect(zone).toBeTruthy();
    if (!zone) {
      return;
    }
    const story = storyFromZone(zone);
    expect(story.position_shown).toBe(false);
    expect(story.position_pct).toBeNull();
    expect(story.relative_order_line).toBeNull();
    expect(story.q_A_display).toBeNull();
    expect(zone.value_display).toBe("—");
  });

  it("keeps hover short and click as the persisted zone story", () => {
    const catalog = historicalCatalog(true);
    const geoid = catalog.zones[0]?.geoid ?? "";
    let state = reduceInteraction(initialInteractionState(), { type: "hover", geoid }, catalog);
    const hover = hoverFromState(state, catalog);
    expect(hover?.line).toBe(`Zone ${geoid} · Own 03:00 position`);
    expect(hover?.line).not.toMatch(/q_A|0\.2000/);
    expect(detailFromState(state, catalog)).toBeNull();

    state = reduceInteraction(state, { type: "select", geoid }, catalog);
    state = reduceInteraction(state, { type: "hover", geoid: null }, catalog);
    const detail = detailFromState(state, catalog);
    expect(detail?.geoid).toBe(geoid);
    expect(detail?.observation_label).toBe("15 Jul 2024 · 03:00 local");
    expect(detail?.source_story).toBe("Replay evidence");
    expect(detail?.relative_order_line).toMatch(/Relative order within this analysis/);
    expect(detail?.q_A_display).toBe("0.2000");
  });
});
