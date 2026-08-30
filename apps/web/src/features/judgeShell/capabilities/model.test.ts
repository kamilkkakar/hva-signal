import { describe, expect, it } from "vitest";
import {
  ACTION_MATURITY,
  HEATDOSE_MATURITY,
  SIGNAL_A_MATURITY,
  SIGNAL_B_MATURITY,
} from "./copy";
import {
  CAPABILITY_ROWS,
  capabilityRow,
  groupCapabilityBands,
  isUnpublishedNumericCapability,
  presentCapabilityExpansion,
} from "./model";

describe("capability expansion model", () => {
  it("places A, cached B, and Action on this surface", () => {
    expect(capabilityRow("signal_a").maturity).toBe(SIGNAL_A_MATURITY);
    expect(capabilityRow("action").maturity).toBe(ACTION_MATURITY);
    expect(capabilityRow("signal_a").band).toBe("on_this_surface");
    expect(capabilityRow("action").band).toBe("on_this_surface");
    expect(capabilityRow("signal_b").band).toBe("on_this_surface");
    expect(
      CAPABILITY_ROWS.filter((row) => row.band === "on_this_surface").map((row) => row.id),
    ).toEqual(["signal_a", "action", "signal_b"]);
  });

  it("promotes B as cached evidence and keeps search/geo/live disabled", () => {
    expect(capabilityRow("signal_b").maturity).toBe(SIGNAL_B_MATURITY);
    expect(capabilityRow("signal_b").maturity).toBe("AVAILABLE NOW — CACHED EVIDENCE");
    expect(capabilityRow("place_search").maturity).toBe("DISABLED");
    expect(capabilityRow("geography_resolve").maturity).toBe("DISABLED");
    expect(capabilityRow("hosted_live").maturity).toBe("DISABLED");
  });

  it("marks HeatDose, AfterHeat, WBGT, and probability as unpublished numbers", () => {
    expect(capabilityRow("heatdose").maturity).toBe(HEATDOSE_MATURITY);
    expect(capabilityRow("heatdose").numericPublic).toBe(false);
    expect(isUnpublishedNumericCapability("heatdose")).toBe(true);
    expect(isUnpublishedNumericCapability("afterheat")).toBe(true);
    expect(isUnpublishedNumericCapability("wbgt")).toBe(true);
    expect(isUnpublishedNumericCapability("probability")).toBe(true);
    expect(isUnpublishedNumericCapability("signal_a")).toBe(false);
  });

  it("presents three bands without promoting gated rows", () => {
    const view = presentCapabilityExpansion();
    const bands = groupCapabilityBands();
    expect(bands.map((band) => band.id)).toEqual([
      "on_this_surface",
      "next_gated",
      "in_development",
    ]);
    expect(view.spine).toEqual([
      "OBSERVE",
      "CONTEXTUALIZE",
      "EXPOSURE",
      "STRESS",
      "ANTICIPATE",
      "ACT",
    ]);
    expect(view.bands[1]?.rows.some((row) => row.maturity.includes("AVAILABLE NOW"))).toBe(
      false,
    );
    expect(view.bands[2]?.rows.some((row) => row.maturity.includes("AVAILABLE NOW"))).toBe(
      false,
    );
  });
});
