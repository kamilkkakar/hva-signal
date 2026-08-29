import { describe, expect, it } from "vitest";
import {
  ARCHITECTURE_THERMAL_DIFF_MESSAGE,
  mapLayerFromLimitations,
  rankingPresentation,
} from "./mapLayer";

describe("mapLayerFromLimitations", () => {
  it("defaults to INTERVENTION PRIORITY", () => {
    const layer = mapLayerFromLimitations([]);
    expect(layer.label).toBe("INTERVENTION PRIORITY");
    expect(layer.allowPriorityChoropleth).toBe(true);
  });

  it("drops INTERVENTION PRIORITY when thermal differentiation is insufficient", () => {
    const layer = mapLayerFromLimitations([
      "THERMAL_SPATIAL_DIFFERENTIATION_INSUFFICIENT",
    ]);
    expect(layer.label).not.toContain("INTERVENTION PRIORITY");
    expect(layer.label).toBe(
      "CONTEXTUAL PREPAREDNESS PRIORITY — THERMAL DIFFERENTIATION UNAVAILABLE",
    );
    expect(layer.message).toBe(ARCHITECTURE_THERMAL_DIFF_MESSAGE);
    expect(layer.allowPriorityChoropleth).toBe(false);
  });

  it("does not label insufficient reference as Decision 8 contextual fallback", () => {
    const layer = mapLayerFromLimitations(["INSUFFICIENT_REFERENCE"]);
    expect(layer.label).not.toBe(
      "CONTEXTUAL PREPAREDNESS PRIORITY — THERMAL DIFFERENTIATION UNAVAILABLE",
    );
    expect(layer.label).toBe("THERMAL ORDERING NOT SUPPORTED");
    expect(layer.allowPriorityChoropleth).toBe(false);
  });
});

describe("rankingPresentation", () => {
  it("stays INSUFFICIENT_EVIDENCE with no zones and invents no scores", () => {
    const presentation = rankingPresentation(undefined);
    expect(presentation.state).toBe("INSUFFICIENT_EVIDENCE");
    expect(presentation.scores).toEqual([]);
  });

  it("treats an empty zone list as INSUFFICIENT_EVIDENCE, not as safe", () => {
    const presentation = rankingPresentation([]);
    expect(presentation.state).toBe("INSUFFICIENT_EVIDENCE");
    expect(presentation.scores).toEqual([]);
  });

  it("does not rank zones that are not marked ranked", () => {
    const presentation = rankingPresentation([
      { zone_id: "z1", ranked: false },
    ]);
    expect(presentation.state).toBe("INSUFFICIENT_EVIDENCE");
    expect(presentation.scores).toEqual([]);
  });

  it("does not invent choropleth scores from probability values", () => {
    const presentation = rankingPresentation([
      {
        zone_id: "z1",
        ranked: false,
        probability: { status: "ok", value: 0.91 },
      },
    ]);
    expect(presentation.state).toBe("INSUFFICIENT_EVIDENCE");
    expect(presentation.scores).toEqual([]);
  });

  it("keeps scores empty even when a zone is marked ranked", () => {
    const presentation = rankingPresentation([
      { zone_id: "z1", ranked: true },
    ]);
    expect(presentation.state).toBe("READY");
    expect(presentation.scores).toEqual([]);
  });

  it("treats FULL_REFERENCE + SUFFICIENT ranked zones as ordering available without inventing scores", () => {
    const presentation = rankingPresentation([
      { zone_id: "04013107401", ranked: true },
      { zone_id: "04013107500", ranked: true },
    ]);
    expect(presentation.state).toBe("READY");
    expect(presentation.scores).toEqual([]);
  });
});
