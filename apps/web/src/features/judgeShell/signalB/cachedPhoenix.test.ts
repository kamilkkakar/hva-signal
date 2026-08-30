import { describe, expect, it } from "vitest";
import { presentSelectedTime } from "@/features/signals/presentation";
import {
  CACHED_B_FINGERPRINT,
  CACHED_B_WORDING,
  phoenixDemoCachedSelectedTime,
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
    expect(blob).not.toMatch(/\\bLIVE\\b/);
    expect(blob).not.toContain("CURRENT CONDITIONS");
    expect(blob).not.toContain("q_A");
    expect(GATE1_TCM_JOINS).toBe("0/25");
  });
});
