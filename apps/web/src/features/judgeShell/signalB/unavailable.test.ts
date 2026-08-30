import { createElement } from "react";
import { renderToStaticMarkup } from "react-dom/server";
import { describe, expect, it } from "vitest";
import { SIGNAL_B_NEUTRAL_MAP_ENABLED } from "@/features/analysisMap/signalBMapGate";
import { presentSignalBMap } from "@/features/analysisMap/signalBPresentation";
import { defaultSignalFeatureFlags } from "@/features/signals/flags";
import { SignalBUnavailableDisclosure } from "./SignalBUnavailableDisclosure";
import {
  GATE1_EXPECTED_ZONE_COUNT,
  GATE1_REASON_CODE,
  GATE1_TCM_JOINS,
  GATE1_VALID_ZONE_COUNT,
  HVA_PUBLIC_TWO_SIGNAL_FLAG,
  P1_LANDING_SELECTED_TIME_REQUESTED,
  PUBLIC_SIGNAL_B,
  VITE_LIVE_DEMO_CONFIRMATION_FLAG,
  VITE_SELECTED_TIME_SNAPSHOT_FLAG,
} from "./publicBGate";
import {
  phoenixDemoUnavailableSelectedTime,
  phoenixDemoUnavailableSelectedTimeView,
} from "./unavailable";

describe("Signal B unavailable contract", () => {
  it("enables cached Public B and keeps live-demo plus landing request off", () => {
    const env = import.meta.env as Record<string, string | boolean | undefined>;
    expect(PUBLIC_SIGNAL_B).toBe(true);
    expect(P1_LANDING_SELECTED_TIME_REQUESTED).toBe(false);
    expect(defaultSignalFeatureFlags().selectedTimeSnapshotInterface).toBe(true);
    expect(defaultSignalFeatureFlags().liveDemoConfirmation).toBe(false);
    expect(SIGNAL_B_NEUTRAL_MAP_ENABLED).toBe(true);
    expect(env[VITE_SELECTED_TIME_SNAPSHOT_FLAG]).not.toBe("true");
    expect(env[VITE_SELECTED_TIME_SNAPSHOT_FLAG]).not.toBe("1");
    expect(env[VITE_LIVE_DEMO_CONFIRMATION_FLAG]).not.toBe("true");
    expect(env[VITE_LIVE_DEMO_CONFIRMATION_FLAG]).not.toBe("1");
    expect(HVA_PUBLIC_TWO_SIGNAL_FLAG).toBe("HVA_PUBLIC_TWO_SIGNAL");
  });

  it("presents GATE 1 unavailable selected-time with no fabricated °C", () => {
    const section = phoenixDemoUnavailableSelectedTime();
    const view = phoenixDemoUnavailableSelectedTimeView();
    expect(section.availability).toBe("UNAVAILABLE");
    expect(section.reason_code).toBe(GATE1_REASON_CODE);
    expect(section.data_status).toBe("unavailable");
    expect(section.reference_version).toBeNull();
    expect(section.reference_source).toBeNull();
    expect(section.zones).toEqual([]);
    expect(section.temperature_min_c).toBeNull();
    expect(section.temperature_max_c).toBeNull();
    expect(section.valid_zone_count).toBe(GATE1_VALID_ZONE_COUNT);
    expect(section.expected_zone_count).toBe(GATE1_EXPECTED_ZONE_COUNT);
    expect(GATE1_TCM_JOINS).toBe("0/25");
    expect(view.ux).toBe("b_unavailable");
    expect(view.stamp).toBe("UNAVAILABLE");
    expect(view.source).toBe("UNAVAILABLE");
    expect(view.live_tape).toBe(false);
    expect(view.show_live_demo).toBe(false);
    expect(view.range_label).toBeNull();
    expect(view.coverage_label).toBe("Zones 0/25");
    expect(view.copy.toLowerCase()).toContain("not treated as cool or safe");
    expect(view.copy.toLowerCase()).not.toContain("fortyguard live");
    expect(view.copy).not.toMatch(/AVAILABLE NOW/);
  });

  it("renders disclosure chrome without temperatures or a reference version", () => {
    const html = renderToStaticMarkup(createElement(SignalBUnavailableDisclosure));
    expect(html).toContain('data-testid="signal-b-unavailable-disclosure"');
    expect(html).toContain('data-public-signal-b="disabled"');
    expect(html).toContain('data-gate1="stands"');
    expect(html).toContain('data-tcm-joins="0/25"');
    expect(html).toContain('data-capability="integration-testing"');
    expect(html).toContain('data-testid="signal-b"');
    expect(html).toContain("UNAVAILABLE");
    expect(html).toContain("Zones 0/25");
    expect(html).not.toContain("°C");
    expect(html).not.toContain("reference_version");
    expect(html).not.toContain("PHX_ZTSI_REF");
    expect(html).not.toContain("AVAILABLE NOW");
    expect(html.toLowerCase()).not.toContain("fortyguard live");
  });

  it("keeps the B map gated off and empty for the unavailable contract", () => {
    const presentation = presentSignalBMap({
      snapshot: null,
      geometry: null,
      availability: "unavailable",
    });
    expect(presentation.visualState).toBe("unavailable");
    expect(presentation.collection.features).toHaveLength(0);
    expect(presentation.validFillCount).toBe(0);
    expect(presentation.tableRows).toEqual([]);
  });
});
