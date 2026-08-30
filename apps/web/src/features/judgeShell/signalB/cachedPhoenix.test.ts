import { describe, expect, it } from "vitest";
import { presentSelectedTime } from "@/features/signals/presentation";
import {
  CACHED_B_FINGERPRINT,
  CACHED_B_WORDING,
  phoenixDemoCachedSelectedTime,
  presentPublicCachedB,
} from "./cachedPhoenix";
import { GATE1_TCM_JOINS, PUBLIC_SIGNAL_B } from "./publicBGate";

describe("cached phoenix Signal B bind", () => {
  it("exposes 25/25 cached evidence without live wording", () => {
    const section = phoenixDemoCachedSelectedTime();
    const view = presentSelectedTime(section, { liveDemoConfirmation: false });
    expect(PUBLIC_SIGNAL_B).toBe(true);
    expect(CACHED_B_WORDING).toBe("AVAILABLE NOW — CACHED EVIDENCE");
    expect(CACHED_B_FINGERPRINT).toHaveLength(64);
    expect(section.valid_zone_count).toBe(25);
    expect(section.expected_zone_count).toBe(25);
    expect(section.zones).toHaveLength(25);
    expect(section.provenance_source).toBe("fortyguard_cached");
    expect(section.data_status).toBe("cached");
    expect(section.reference_version).toBeNull();
    expect(section.ready_scene).toBe("cached");
    expect(view.stamp).toBe("CACHED");
    expect(view.source).toBe("CACHED");
    expect(view.coverage_label).toBe("Zones 25/25");
    expect(view.show_live_demo).toBe(false);
    expect(view.live_tape).toBe(false);
    expect(view.title).toBe("Selected-Time Thermal Snapshot");
    const blob = [view.stamp, view.source ?? "", view.copy, CACHED_B_WORDING].join(" ");
    expect(blob).not.toMatch(/\bLIVE\b/);
    expect(blob).not.toContain("CURRENT CONDITIONS");
    expect(blob).not.toContain("q_A");
    expect(GATE1_TCM_JOINS).toBe("0/25");
  });

  it("publishes rounded public facts without ranking or live wording", () => {
    const facts = presentPublicCachedB("04013106400");
    expect(facts.wording).toBe(CACHED_B_WORDING);
    expect(facts.coverage).toBe("25/25");
    expect(facts.source).toBe("CACHED");
    expect(facts.provenance).toBe("fortyguard_cached");
    expect(facts.rangeLabel).toBe("33.5–33.7 °C");
    expect(facts.zoneAverageLabel).toMatch(/^\d+\.\d °C$/);
    expect(facts.selectedLabel).toMatch(/^\d+\.\d °C$/);
    expect(facts.footnote).toBe("not q_A / not Decision 8");
    expect(facts.rangeLabel).not.toMatch(/\d\.\d{2,}/);
    const primary = [facts.wording, facts.coverage, facts.source, facts.zoneAverageLabel, facts.rangeLabel, facts.selectedLabel].join(" ");
    expect(primary).not.toMatch(/\bLIVE\b/);
    expect(primary).not.toMatch(/rank|priority|Decision 8|q_A/i);
  });
});
