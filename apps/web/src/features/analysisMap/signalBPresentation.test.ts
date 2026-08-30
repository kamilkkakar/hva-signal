import { describe, expect, it } from "vitest";
import { signalBFillPaint, signalBValidZoneFill } from "./signalBFill";
import { bindSignalBGeometry } from "./signalBGeometry";
import { signalBHoverFromProperties } from "./signalBHover";
import {
  afternoonFlatSnapshot,
  afternoonPartialSnapshot,
  nightStructuredSnapshot,
  signalBFixtureGeometry,
  SIGNAL_B_FIXTURE_ZONE_COUNT,
} from "./fixtures/signalB25ZoneFixture";
import {
  CURRENT_AOI_AUTOSTRETCH,
  PERCENTILE_AUTOSTRETCH,
  RANK_IMPLICATION,
  SIGNAL_B_LAYER_TITLE,
  SIGNAL_B_NEUTRAL_FILL,
  formatSignalBTemperatureC,
} from "./signalBPolicy";
import { presentSignalBMap } from "./signalBPresentation";
import { signalBTableRows } from "./signalBTable";

describe("V1 locks", () => {
  it("freezes autostretch and rank off", () => {
    expect(CURRENT_AOI_AUTOSTRETCH).toBe(false);
    expect(PERCENTILE_AUTOSTRETCH).toBe(false);
    expect(RANK_IMPLICATION).toBe(false);
    expect(SIGNAL_B_LAYER_TITLE).toBe("Selected-Time Thermal Snapshot");
  });
});

describe("presentSignalBMap", () => {
  it("can still be gated off when explicitly disabled", () => {
    const presentation = presentSignalBMap({
      enabled: false,
      snapshot: afternoonFlatSnapshot(),
      geometry: signalBFixtureGeometry(),
    });
    expect(presentation.visualState).toBe("gated_off");
    expect(presentation.layerTitle).toBe("Selected-Time Thermal Snapshot");
    expect(presentation.collection.features).toHaveLength(0);
    expect(presentation.autoContrastBanner).toBeNull();
  });

  it("presents 25 zones with shared fill and an ID-sorted table", () => {
    const snapshot = afternoonFlatSnapshot();
    const presentation = presentSignalBMap({
      enabled: true,
      snapshot,
      geometry: signalBFixtureGeometry(),
      availability: "ready",
    });
    expect(presentation.visualState).toBe("ready");
    expect(presentation.outlineCount).toBe(SIGNAL_B_FIXTURE_ZONE_COUNT);
    expect(presentation.validFillCount).toBe(SIGNAL_B_FIXTURE_ZONE_COUNT);
    expect(presentation.tableRows).toHaveLength(SIGNAL_B_FIXTURE_ZONE_COUNT);
    expect(presentation.layerTitle).toBe("Selected-Time Thermal Snapshot");
    expect(presentation.autoContrastBanner).toBeNull();
    const ids = presentation.tableRows.map((row) => row.zone_id);
    expect(ids).toEqual([...ids].sort((a, b) => a.localeCompare(b)));
    expect(presentation.fillPaint["fill-color"]).toBe(SIGNAL_B_NEUTRAL_FILL);
  });

  it("keeps the same fill for a 0.200 °C field and a ~3 °C field", () => {
    const flat = presentSignalBMap({
      enabled: true,
      snapshot: afternoonFlatSnapshot(),
      geometry: signalBFixtureGeometry(),
      availability: "ready",
    });
    const night = presentSignalBMap({
      enabled: true,
      snapshot: nightStructuredSnapshot(),
      geometry: signalBFixtureGeometry(),
      availability: "ready",
    });
    expect(flat.fillPaint).toEqual(night.fillPaint);
    expect(flat.fillPaint).toEqual(signalBFillPaint());
    expect(signalBValidZoneFill()).toEqual(signalBValidZoneFill());
    const flatSpread =
      (flat.snapshotFacts.temperature_max_c ?? 0) -
      (flat.snapshotFacts.temperature_min_c ?? 0);
    const nightSpread =
      (night.snapshotFacts.temperature_max_c ?? 0) -
      (night.snapshotFacts.temperature_min_c ?? 0);
    expect(flatSpread).toBeCloseTo(0.2, 8);
    expect(nightSpread).toBeGreaterThan(2.5);
    expect(flat.autoContrastBanner).toBeNull();
    expect(night.autoContrastBanner).toBeNull();
  });

  it("does not invent rank, q_A, or a value-mapped color domain", () => {
    const presentation = presentSignalBMap({
      enabled: true,
      snapshot: nightStructuredSnapshot(),
      geometry: signalBFixtureGeometry(),
      availability: "ready",
    });
    for (const feature of presentation.collection.features) {
      expect(feature.properties).not.toHaveProperty("backend_order");
      expect(feature.properties).not.toHaveProperty("q_A");
      expect(feature.properties).not.toHaveProperty("ranked");
      expect(JSON.stringify(feature.properties)).not.toMatch(/rank/i);
    }
    expect(JSON.stringify(presentation.fillPaint)).not.toContain("mean_temperature_c");
    expect(JSON.stringify(presentation.fillPaint)).not.toContain("temperature_min_c");
    expect(JSON.stringify(presentation.fillPaint)).not.toContain("interpolate");
    expect(presentation.snapshotFacts.factText).toMatch(/zone means in this snapshot/);
    expect(presentation.meaningCopy).not.toMatch(/q_A|Decision 8|rank|priority/i);
  });

  it("shows missing zones as an em dash, never 0 °C", () => {
    const presentation = presentSignalBMap({
      enabled: true,
      snapshot: afternoonPartialSnapshot(),
      geometry: signalBFixtureGeometry(),
      availability: "partial",
    });
    expect(presentation.visualState).toBe("partial");
    const missing = presentation.tableRows.find(
      (row) => row.coverage_status === "missing",
    );
    expect(missing).toBeDefined();
    expect(missing?.mean_temperature_c).toBeNull();
    expect(missing?.display_temperature).toBe("—");
    expect(formatSignalBTemperatureC(null)).toBe("—");
    expect(formatSignalBTemperatureC(0)).toBe("0.0 °C");
  });
});

describe("signalBTableRows", () => {
  it("sorts by zone_id even when temperatures are reversed", () => {
    const snapshot = nightStructuredSnapshot();
    const reversed = {
      ...snapshot,
      zones: [...snapshot.zones].sort(
        (a, b) => (b.mean_temperature_c ?? 0) - (a.mean_temperature_c ?? 0),
      ),
    };
    const rows = signalBTableRows({ snapshot: reversed });
    const ids = rows.map((row) => row.zone_id);
    expect(ids).toEqual([...ids].sort((a, b) => a.localeCompare(b)));
    expect(rows[0]?.mean_temperature_c).not.toBeGreaterThan(
      rows[rows.length - 1]?.mean_temperature_c ?? 0,
    );
  });
});

describe("bindSignalBGeometry", () => {
  it("joins 25 schematic zones without writing a rank field", () => {
    const bound = bindSignalBGeometry({
      geometry: signalBFixtureGeometry(),
      snapshot: afternoonFlatSnapshot(),
    });
    expect(bound.ok).toBe(true);
    if (!bound.ok) {
      return;
    }
    expect(bound.joinedCount).toBe(25);
    expect(bound.collection.features.every((feature) => !("backend_order" in feature.properties))).toBe(
      true,
    );
  });
});

describe("signalBHoverFromProperties", () => {
  it("exposes absolute °C and coverage only", () => {
    const hover = signalBHoverFromProperties({
      zone_id: "FIX-0455000-03",
      mean_temperature_c: 40.111,
      coverage_status: "valid",
    });
    expect(hover).toEqual({
      zone_id: "FIX-0455000-03",
      display_temperature: "40.1 °C",
      coverage_status: "valid",
      units: "celsius",
      aggregation_method: "centroid_within_mean",
    });
    expect(JSON.stringify(hover)).not.toMatch(/order|q_A|rank/i);
  });
});
