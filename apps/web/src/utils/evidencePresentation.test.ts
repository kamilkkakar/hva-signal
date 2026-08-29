import { describe, expect, it } from "vitest";
import { ARCHITECTURE_THERMAL_DIFF_MESSAGE } from "./mapLayer";
import {
  decision8EvidencePanel,
  decisionThermalLimitation,
  evidenceGraphPresentation,
  probabilityFieldsPresentation,
  stallCopy,
} from "./evidencePresentation";

const PERCENT_PROBABILITY = /\d+(\.\d+)?\s*%|\bpercent(?:age)?\b/i;
const CALIBRATED_PROBABILITY_CLAIM =
  /\d+(\.\d+)?\s*%\s*probability|probability\s*[:=]?\s*\d/i;

describe("evidenceGraphPresentation", () => {
  it("does not treat a missing result as an empty graph (queued jobs)", () => {
    const presentation = evidenceGraphPresentation(undefined);
    expect(presentation.state).toBe("AWAITING_RESULT");
    expect(presentation.empty).toBe(false);
    expect(presentation.populated).toBe(false);
    expect(presentation.copy).toMatch(/not available|until .+ result/i);
    expect(presentation.copy).not.toMatch(/empty/i);
  });

  it("does not treat a null result as an empty or populated graph", () => {
    const presentation = evidenceGraphPresentation(null);
    expect(presentation.state).toBe("AWAITING_RESULT");
    expect(presentation.empty).toBe(false);
    expect(presentation.populated).toBe(false);
  });

  it("marks GRAPH_ABSENT when a result has no evidence_graph field", () => {
    const presentation = evidenceGraphPresentation({ zones: [] });
    expect(presentation.state).toBe("GRAPH_ABSENT");
    expect(presentation.empty).toBe(false);
    expect(presentation.populated).toBe(false);
  });

  it("marks GRAPH_EMPTY when the API returns an empty evidence graph", () => {
    const presentation = evidenceGraphPresentation({
      evidence_graph: { nodes: [], edges: [] },
    });
    expect(presentation.state).toBe("GRAPH_EMPTY");
    expect(presentation.empty).toBe(true);
    expect(presentation.populated).toBe(false);
    expect(presentation.copy).toMatch(/empty/i);
    expect(presentation.copy).toMatch(/not treated as safe|insufficient/i);
  });

  it("marks GRAPH_POPULATED when nodes or edges exist and invents no ranking", () => {
    const presentation = evidenceGraphPresentation({
      evidence_graph: {
        nodes: [{ id: "n1" }],
        edges: [],
      },
    });
    expect(presentation.state).toBe("GRAPH_POPULATED");
    expect(presentation.empty).toBe(false);
    expect(presentation.populated).toBe(true);
    expect(presentation.copy).not.toMatch(/rank|choropleth|score/i);
  });

  it("treats non-array graph collections as empty, not populated", () => {
    const presentation = evidenceGraphPresentation({
      evidence_graph: { nodes: "oops" as unknown as [], edges: null },
    });
    expect(presentation.state).toBe("GRAPH_EMPTY");
    expect(presentation.populated).toBe(false);
  });
});

describe("probabilityFieldsPresentation", () => {
  it("does not invent a probability field when zones are missing", () => {
    expect(probabilityFieldsPresentation(undefined)).toBeNull();
    expect(probabilityFieldsPresentation([])).toBeNull();
    expect(probabilityFieldsPresentation([{ zone_id: "z1" }])).toBeNull();
  });

  it("never renders a numeric value as a percent or calibrated probability", () => {
    const presentation = probabilityFieldsPresentation([
      {
        zone_id: "z1",
        ranked: true,
        probability: { status: "ok", value: 0.87 },
      },
      {
        zone_id: "z2",
        probability: { status: "ok", value: 50 },
      },
    ]);
    expect(presentation).not.toBeNull();
    expect(presentation?.shown).toBe(true);
    expect(presentation?.label).toMatch(/blocked|insufficient|not a probability|gate 0/i);
    expect(presentation?.label).not.toMatch(PERCENT_PROBABILITY);
    expect(presentation?.label).not.toMatch(CALIBRATED_PROBABILITY_CLAIM);
    expect(presentation?.label).not.toContain("0.87");
    expect(presentation?.label).not.toContain("87");
    expect(presentation?.label).not.toContain("50");
    expect(JSON.stringify(presentation)).not.toMatch(PERCENT_PROBABILITY);
  });

  it("blocks the field even when EngineResult status is insufficient_evidence", () => {
    const presentation = probabilityFieldsPresentation([
      {
        zone_id: "z1",
        probability: { status: "insufficient_evidence", value: null },
      },
    ]);
    expect(presentation?.label).toMatch(/insufficient evidence|not a probability|blocked|gate 0/i);
    expect(presentation?.label).not.toMatch(PERCENT_PROBABILITY);
  });
});

describe("decisionThermalLimitation", () => {
  it("shows the architecture message in the rail when a completed job flags thermal differentiation", () => {
    const message = decisionThermalLimitation({
      status: "complete",
      limitations: ["THERMAL_SPATIAL_DIFFERENTIATION_INSUFFICIENT"],
    });
    expect(message).toBe(ARCHITECTURE_THERMAL_DIFF_MESSAGE);
  });

  it("shows the same message for a partial completed result", () => {
    const message = decisionThermalLimitation({
      status: "partial",
      limitations: ["THERMAL_SPATIAL_DIFFERENTIATION_INSUFFICIENT"],
    });
    expect(message).toBe(ARCHITECTURE_THERMAL_DIFF_MESSAGE);
  });

  it("does not surface the architecture limitation before a result completes", () => {
    expect(
      decisionThermalLimitation({
        status: "queued",
        limitations: ["THERMAL_SPATIAL_DIFFERENTIATION_INSUFFICIENT"],
      }),
    ).toBeNull();
    expect(
      decisionThermalLimitation({
        status: "computing",
        limitations: ["THERMAL_SPATIAL_DIFFERENTIATION_INSUFFICIENT"],
      }),
    ).toBeNull();
    expect(
      decisionThermalLimitation({
        status: "complete",
        limitations: [],
      }),
    ).toBeNull();
  });

  it("does not use the Decision 8 fallback message for insufficient reference", () => {
    expect(
      decisionThermalLimitation({
        status: "complete",
        limitations: ["INSUFFICIENT_REFERENCE"],
      }),
    ).toBeNull();
  });
});

describe("decision8EvidencePanel", () => {
  it("exposes first-class Decision 8 fallback evidence without treating it as an API error", () => {
    const panel = decision8EvidencePanel(      {
        system_limitations: ["THERMAL_SPATIAL_DIFFERENTIATION_INSUFFICIENT"],
        versions: { area_config_version: "PHX_AREA_CONFIG_V1" },
        hazard_spread: {
        policy_version:
          "PHX_NORMALIZED_HAZARD_SPREAD_V1_TOP3_BOTTOM3_QA_FLOOR_0P10",
        reference_version: "PHX_ZTSI_REF_V1",
        zone_geometry_version: "US_CENSUS_TIGERLINE",
        input_quantity: "q_A",
        metric: "TOP3_BOTTOM3_MEAN_DIFFERENCE",
        top_group_size: 3,
        bottom_group_size: 3,
        floor: 0.1,
        comparison_operator: ">=",
        observed_spread: 0.07,
        differentiation_state: "INSUFFICIENT",
        reference_quality: "FULL_REFERENCE",
        suppression_reason: "normalized hazard spread S is below the frozen Decision 8 floor",
        historical_years: [2022, 2023, 2024],
        reference_hour: "03:00",
      },
    });
    expect(panel).not.toBeNull();
    expect(panel?.title).toBe("THERMAL ORDERING NOT SUPPORTED");
    expect(panel?.observedSpread).toBe(0.07);
    expect(panel?.requiredSpread).toBe(0.1);
    expect(panel?.statistic).toBe("TOP3_BOTTOM3_MEAN_DIFFERENCE");
    expect(panel?.tailGroupSize).toBe("3 / 25 per tail");
    expect(panel?.areaConfigVersion).toBe("PHX_AREA_CONFIG_V1");
    expect(panel?.policyVersion).toBe(
      "PHX_NORMALIZED_HAZARD_SPREAD_V1_TOP3_BOTTOM3_QA_FLOOR_0P10",
    );
    expect(panel?.referenceVersion).toBe("PHX_ZTSI_REF_V1");
    expect(panel?.zoneGeometryVersion).toBe("US_CENSUS_TIGERLINE");
    expect(panel?.historicalYears).toEqual([2022, 2023, 2024]);
    expect(panel?.referenceHour).toBe("03:00");
    expect(panel?.referenceQuality).toBe("FULL_REFERENCE");
    expect(panel?.result).toBe("THERMAL_SPATIAL_DIFFERENTIATION_INSUFFICIENT");
  });

  it("does not present insufficient reference as Decision 8 insufficient differentiation", () => {
    expect(
      decision8EvidencePanel({
        system_limitations: ["INSUFFICIENT_REFERENCE"],
        hazard_spread: {
          differentiation_state: "NOT_EVALUATED",
          reference_quality: "INSUFFICIENT_REFERENCE",
          metric: "TOP3_BOTTOM3_MEAN_DIFFERENCE",
        },
      }),
    ).toBeNull();
  });

  it("reads AreaConfig version, S, floor, and FULL_REFERENCE from a job-path INSUFFICIENT payload", () => {
    const panel = decision8EvidencePanel({
      versions: {
        area_config_version: "PHX_AREA_CONFIG_V1",
        zone_geometry_version:
          "US_CENSUS_TIGERLINE.CENSUS_TRACT.2025.AZ.PHX_DEMO_AOI_POLICY_V1.3f16870f",
        hazard_spread_policy_version:
          "PHX_NORMALIZED_HAZARD_SPREAD_V1_TOP3_BOTTOM3_QA_FLOOR_0P10",
      },
      reference_quality: "FULL_REFERENCE",
      thermal_differentiation_state: "INSUFFICIENT",
      system_limitations: ["THERMAL_SPATIAL_DIFFERENTIATION_INSUFFICIENT"],
      limitations: [
        "CONTEXTUAL PREPAREDNESS PRIORITY — THERMAL DIFFERENTIATION UNAVAILABLE",
      ],
      hazard_spread: {
        policy_version:
          "PHX_NORMALIZED_HAZARD_SPREAD_V1_TOP3_BOTTOM3_QA_FLOOR_0P10",
        reference_version:
          "PHX_ZTSI_REF_V1__US_CENSUS_TIGERLINE.CENSUS_TRACT.2025.AZ.PHX_DEMO_AOI_POLICY_V1.3f16870f__ANCHOR_2025-07-15__S2_PM15_CALENDAR_DAYS__YEARS_2022_2023_2024__HOUR_0300_LOCAL__GRANULARITY_100M",
        zone_geometry_version:
          "US_CENSUS_TIGERLINE.CENSUS_TRACT.2025.AZ.PHX_DEMO_AOI_POLICY_V1.3f16870f",
        input_quantity: "q_A",
        metric: "TOP3_BOTTOM3_MEAN_DIFFERENCE",
        top_group_size: 3,
        bottom_group_size: 3,
        floor: 0.1,
        comparison_operator: ">=",
        observed_spread: 0.04396654719235371,
        differentiation_state: "INSUFFICIENT",
        reference_quality: "FULL_REFERENCE",
        suppression_reason: "normalized hazard spread S is below the frozen Decision 8 floor",
        historical_years: [2022, 2023, 2024],
        reference_hour: "03:00",
      },
    });
    expect(panel?.title).toBe("THERMAL ORDERING NOT SUPPORTED");
    expect(panel?.areaConfigVersion).toBe("PHX_AREA_CONFIG_V1");
    expect(panel?.observedSpread).toBe(0.04396654719235371);
    expect(panel?.requiredSpread).toBe(0.1);
    expect(panel?.statistic).toBe("TOP3_BOTTOM3_MEAN_DIFFERENCE");
    expect(panel?.tailGroupSize).toBe("3 / 25 per tail");
    expect(panel?.referenceQuality).toBe("FULL_REFERENCE");
    expect(panel?.reason).not.toBeNull();
    expect(panel?.floorDisplay).toBe("0.10 q_A units");
    expect(panel?.floorDisplay).not.toMatch(/%|probability|confidence|°C|10%/i);
  });

  it("exposes Decision 8 provenance when differentiation is sufficient", () => {
    const panel = decision8EvidencePanel({
      versions: {
        area_config_version: "PHX_AREA_CONFIG_V1",
        zone_geometry_version:
          "US_CENSUS_TIGERLINE.CENSUS_TRACT.2025.AZ.PHX_DEMO_AOI_POLICY_V1.3f16870f",
        hazard_spread_policy_version:
          "PHX_NORMALIZED_HAZARD_SPREAD_V1_TOP3_BOTTOM3_QA_FLOOR_0P10",
      },
      reference_quality: "FULL_REFERENCE",
      thermal_differentiation_state: "SUFFICIENT",
      hazard_spread: {
        policy_version:
          "PHX_NORMALIZED_HAZARD_SPREAD_V1_TOP3_BOTTOM3_QA_FLOOR_0P10",
        reference_version:
          "PHX_ZTSI_REF_V1__US_CENSUS_TIGERLINE.CENSUS_TRACT.2025.AZ.PHX_DEMO_AOI_POLICY_V1.3f16870f__ANCHOR_2025-07-15__S2_PM15_CALENDAR_DAYS__YEARS_2022_2023_2024__HOUR_0300_LOCAL__GRANULARITY_100M",
        zone_geometry_version:
          "US_CENSUS_TIGERLINE.CENSUS_TRACT.2025.AZ.PHX_DEMO_AOI_POLICY_V1.3f16870f",
        input_quantity: "q_A",
        metric: "TOP3_BOTTOM3_MEAN_DIFFERENCE",
        top_group_size: 3,
        bottom_group_size: 3,
        floor: 0.1,
        comparison_operator: ">=",
        observed_spread: 0.1354838709677419,
        differentiation_state: "SUFFICIENT",
        reference_quality: "FULL_REFERENCE",
        suppression_reason: null,
        historical_years: [2022, 2023, 2024],
        reference_hour: "03:00",
      },
    });
    expect(panel).not.toBeNull();
    expect(panel?.observedSpread).toBeCloseTo(0.1354838709677419, 12);
    expect(panel?.policyVersion).toBe(
      "PHX_NORMALIZED_HAZARD_SPREAD_V1_TOP3_BOTTOM3_QA_FLOOR_0P10",
    );
    expect(panel?.referenceVersion).toContain("PHX_ZTSI_REF_V1");
    expect(panel?.zoneGeometryVersion).toBe(
      "US_CENSUS_TIGERLINE.CENSUS_TRACT.2025.AZ.PHX_DEMO_AOI_POLICY_V1.3f16870f",
    );
    expect(panel?.floorDisplay).toBe("0.10 q_A units");
    expect(panel?.result).toBe("SUFFICIENT");
    expect(JSON.stringify(panel)).not.toMatch(
      /\bsafe\b|\bcool\b|not hot|\bbenign\b|heat severity|probability|25\s*\/\s*93/i,
    );
  });
});

describe("stallCopy", () => {
  it("mentions missing orchestration only for queued/in-flight jobs without a result", () => {
    const copy = stallCopy({
      stalled: true,
      status: "queued",
      hasResult: false,
    });
    expect(copy).not.toBeNull();
    expect(copy?.message).toMatch(/Orchestration is not connected yet/i);
    expect(copy?.recoveryHint).toMatch(/orchestration/i);
  });

  it("does not say orchestration is missing when status is complete", () => {
    const copy = stallCopy({
      stalled: true,
      status: "complete",
      hasResult: true,
    });
    expect(copy).not.toBeNull();
    expect(copy?.message).not.toMatch(/Orchestration is not connected yet/i);
    expect(copy?.recoveryHint).not.toMatch(/orchestration/i);
  });

  it("does not say orchestration is missing when status is partial", () => {
    const copy = stallCopy({
      stalled: true,
      status: "partial",
      hasResult: true,
    });
    expect(copy?.message).not.toMatch(/Orchestration is not connected yet/i);
    expect(copy?.recoveryHint).not.toMatch(/orchestration/i);
  });

  it("does not say orchestration is missing when an in-flight job already has a result", () => {
    const copy = stallCopy({
      stalled: true,
      status: "computing",
      hasResult: true,
    });
    expect(copy?.message).not.toMatch(/Orchestration is not connected yet/i);
  });

  it("returns null when the job is not stalled", () => {
    expect(
      stallCopy({ stalled: false, status: "queued", hasResult: false }),
    ).toBeNull();
  });
});
