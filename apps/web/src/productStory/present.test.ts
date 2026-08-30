import { describe, expect, it } from "vitest";
import type { AnalysisResultStub } from "@/api/analysisJobs";
import {
  COMPARISON_SUFFICIENT,
  COMPARISON_TOO_SIMILAR,
  EVIDENCE_LINEAGE_RECORDED,
  FORBIDDEN_PUBLIC_TOKENS,
  REFERENCE_AVAILABLE,
  REFERENCE_NOT_PREPARED,
} from "./copy";
import { presentAnalysisStory, storyPublicChrome } from "./present";
import {
  PUBLIC_GEO_ON_STORY,
  PUBLIC_SEARCH_ON_STORY,
  PUBLIC_SIGNAL_B_ON_STORY,
  STORY_ZONE_COUNT,
} from "./types";

function zone(id: string, permitted: boolean): NonNullable<AnalysisResultStub["zones"]>[number] {
  return {
    zone_id: id,
    ranked: permitted,
    thermal_ordering_permitted: permitted,
    q_A: permitted ? 0.34 : 0.04,
  };
}

function sufficientResult(): AnalysisResultStub {
  return {
    thermal_differentiation_state: "SUFFICIENT",
    reference_quality: "FULL_REFERENCE",
    evidence_graph: { nodes: [{ id: "n1" }], edges: [{ id: "e1" }] },
    hazard_spread: {
      differentiation_state: "SUFFICIENT",
      reference_quality: "FULL_REFERENCE",
      historical_years: [2020, 2021, 2022],
      reference_hour: "03:00",
      observed_spread: 0.13548387096774192,
      floor: 0.1,
    },
    zones: Array.from({ length: 25 }, (_, index) =>
      zone(String(index + 1).padStart(11, "0"), true),
    ),
  };
}

function insufficientResult(): AnalysisResultStub {
  return {
    thermal_differentiation_state: "INSUFFICIENT",
    reference_quality: "FULL_REFERENCE",
    system_limitations: ["THERMAL_SPATIAL_DIFFERENTIATION_INSUFFICIENT"],
    evidence_graph: { nodes: [{ id: "n1" }], edges: [] },
    hazard_spread: {
      differentiation_state: "INSUFFICIENT",
      reference_quality: "FULL_REFERENCE",
      historical_years: [2020, 2021, 2022],
      observed_spread: 0.0439665471923536,
      floor: 0.1,
    },
    zones: [],
  };
}

function publicBlob(view: ReturnType<typeof presentAnalysisStory>): string {
  return storyPublicChrome(view).join("\n");
}

describe("presentAnalysisStory", () => {
  it("maps SUFFICIENT to comparable public copy and hides GRAPH_POPULATED", () => {
    const view = presentAnalysisStory({
      status: "complete",
      result: sufficientResult(),
      areaId: "phoenix-demo",
      analysisTime: "2022-06-30T03:00:00",
      selectedZoneId: "04013061000",
      selectedOrder: 2,
    });

    expect(view.comparison_state).toBe("comparable");
    expect(view.comparison_explanation).toBe(COMPARISON_SUFFICIENT);
    expect(view.headline).toBe("Nighttime heat order is shown");
    expect(view.map_mode).toBe("order_shown");
    expect(view.zone_count).toBe(STORY_ZONE_COUNT);
    expect(view.zone_story.ranked_fill_count).toBe(25);
    expect(view.zone_story.hover_enabled).toBe(true);
    expect(view.zone_story.selected_line).toContain("order 2 of 25");
    expect(view.reference_period_label).toContain(REFERENCE_AVAILABLE);
    expect(view.reference_period_label).toContain("2020–2022");
    expect(view.observation_time).toContain("2022-06-30");
    expect(view.what_this_supports).toContain(COMPARISON_SUFFICIENT);
    expect(view.technical_details.evidence_lineage.recorded).toBe(true);
    expect(view.technical_details.evidence_lineage.label).toBe(
      EVIDENCE_LINEAGE_RECORDED,
    );
    expect(view.technical_details.evidence_lineage.placement).toBe(
      "provenance_only",
    );
    expect(view.technical_details.backend.thermal_differentiation_state).toBe(
      "SUFFICIENT",
    );
    expect(view.technical_details.backend.evidence_graph_state).toBe(
      "GRAPH_POPULATED",
    );

    const chrome = publicBlob(view);
    expect(chrome).not.toContain("GRAPH_POPULATED");
    expect(chrome).not.toContain(EVIDENCE_LINEAGE_RECORDED);
    expect(chrome).not.toContain("SUFFICIENT");
    expect(chrome).not.toContain("q_A");
    expect(chrome).not.toMatch(/°C/);
  });

  it("maps INSUFFICIENT / INSUFFICIENT_EVIDENCE to too-similar copy", () => {
    const view = presentAnalysisStory({
      status: "complete",
      result: insufficientResult(),
      areaId: "phoenix-demo",
      analysisTime: "2022-07-01T03:00:00",
    });

    expect(view.comparison_state).toBe("too_similar");
    expect(view.comparison_explanation).toBe(COMPARISON_TOO_SIMILAR);
    expect(view.headline).toBe(
      "Nighttime patterns are too similar to rank defensibly",
    );
    expect(view.map_mode).toBe("order_withheld");
    expect(view.zone_story.ranked_fill_count).toBe(0);
    expect(view.zone_story.outline_count).toBe(25);
    expect(view.zone_story.hover_enabled).toBe(false);
    expect(view.zone_story.selected_line).toBeNull();
    expect(view.technical_details.backend.ranking_state).toBe(
      "INSUFFICIENT_EVIDENCE",
    );
    expect(view.reference_period_label).toContain(REFERENCE_AVAILABLE);
    expect(view.technical_details.evidence_lineage.label).toBe(
      EVIDENCE_LINEAGE_RECORDED,
    );

    const chrome = publicBlob(view);
    expect(chrome).toContain(COMPARISON_TOO_SIMILAR);
    expect(chrome).not.toContain("INSUFFICIENT_EVIDENCE");
    expect(chrome).not.toContain("INSUFFICIENT EVIDENCE");
    expect(chrome).not.toContain("GRAPH_POPULATED");
    expect(chrome).not.toContain("0.0439665471923536");
    expect(chrome).not.toContain("0.10");
  });

  it("does not treat missing reference as a withheld order", () => {
    const view = presentAnalysisStory({
      status: "complete",
      result: {
        system_limitations: ["INSUFFICIENT_REFERENCE"],
        thermal_differentiation_state: "NOT_EVALUATED",
        reference_quality: "INSUFFICIENT_REFERENCE",
        evidence_graph: { nodes: [{ id: "n1" }], edges: [] },
      },
      areaId: "phoenix-demo",
      analysisTime: "2022-07-01T03:00:00",
    });

    expect(view.comparison_state).toBe("history_unavailable");
    expect(view.map_mode).toBe("history_unavailable");
    expect(view.reference_period_label).toBe(REFERENCE_NOT_PREPARED);
    expect(view.comparison_explanation).not.toBe(COMPARISON_TOO_SIMILAR);
    expect(view.technical_details.evidence_lineage.label).toBe(
      EVIDENCE_LINEAGE_RECORDED,
    );
    expect(publicBlob(view)).not.toContain("GRAPH_POPULATED");
  });

  it("fails closed when SUFFICIENT is claimed without permitted zones", () => {
    const view = presentAnalysisStory({
      status: "complete",
      result: {
        thermal_differentiation_state: "SUFFICIENT",
        hazard_spread: { differentiation_state: "SUFFICIENT" },
        zones: [zone("04013980000", false)],
      },
    });
    expect(view.comparison_state).toBe("not_evaluated");
    expect(view.map_mode).toBe("idle");
    expect(view.zone_story.ranked_fill_count).toBe(0);
  });

  it("awaits in-flight jobs and does not invent an order", () => {
    const view = presentAnalysisStory({
      status: "validating_hazard_spread",
      result: null,
    });
    expect(view.comparison_state).toBe("awaiting");
    expect(view.map_mode).toBe("awaiting");
    expect(view.zone_story.ranked_fill_count).toBe(0);
    expect(view.technical_details.evidence_lineage.recorded).toBe(false);
    expect(view.technical_details.evidence_lineage.label).toBeNull();
  });

  it("keeps public chrome free of method, vendor, and backend stamps", () => {
    const views = [
      presentAnalysisStory({
        status: "complete",
        result: sufficientResult(),
        areaId: "phoenix-demo",
        analysisTime: "2022-06-30T03:00:00",
        selectedZoneId: "1",
        selectedOrder: 1,
      }),
      presentAnalysisStory({
        status: "complete",
        result: insufficientResult(),
        areaId: "phoenix-demo",
        analysisTime: "2022-07-01T03:00:00",
      }),
      presentAnalysisStory({}),
    ];

    for (const view of views) {
      const chrome = publicBlob(view);
      for (const token of FORBIDDEN_PUBLIC_TOKENS) {
        expect(chrome.includes(token), token).toBe(false);
      }
      expect(chrome).not.toMatch(/°C/);
      expect(chrome).not.toMatch(/FortyGuard/i);
    }
  });

  it("does not publish Signal B degrees or enable search / geo", () => {
    expect(PUBLIC_SIGNAL_B_ON_STORY).toBe(false);
    expect(PUBLIC_SEARCH_ON_STORY).toBe(false);
    expect(PUBLIC_GEO_ON_STORY).toBe(false);
    const view = presentAnalysisStory({
      status: "complete",
      result: sufficientResult(),
      areaId: "phoenix-demo",
    });
    expect(view.primary_facts.some((fact) => fact.includes("snapshot"))).toBe(
      true,
    );
    expect(publicBlob(view)).not.toMatch(/°C/);
    expect(view.analysis_area_label).toContain("not the municipality");
  });

  it("leaves method notes in technical details only", () => {
    const view = presentAnalysisStory({
      status: "complete",
      result: sufficientResult(),
    });
    const method = view.technical_details.method_notes.join("\n");
    expect(method).toContain("q_A");
    expect(method).toContain("Decision 8");
    expect(method).toMatch(/\bS\b/);
    expect(publicBlob(view)).not.toContain("q_A");
    expect(publicBlob(view)).not.toContain("Decision 8");
  });
});
