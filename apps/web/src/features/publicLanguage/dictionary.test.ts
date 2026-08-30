import { describe, expect, it } from "vitest";
import {
  DICTIONARY,
  FORBIDDEN_CLAIM_PHRASES,
  FORBIDDEN_PRIMARY_TERMS,
  PUBLIC_NOUN,
  PUBLIC_SENTENCE,
  PUBLIC_STATUS,
  PUBLIC_STATUSES,
  QUALIFIED_CAPABILITY_NOUNS,
  SCAN_NOTES,
  SHIPPED_ALIAS,
  canonicalPublicStatus,
  chromeUsesForbiddenPrimary,
  lookup,
  neverShow,
  publicPrimaryLabel,
  publicStatusForRankingState,
  publicStatusForReady,
  relativeOrderLabel,
  removeFromPrimary,
  shippedAliasForPublicStatus,
  technicalDetailsLabel,
} from "./dictionary";

describe("public language dictionary", () => {
  it("locks the required public mappings", () => {
    expect(publicPrimaryLabel("Decision 8")).toBe(
      "Spatial differentiation check",
    );
    expect(publicPrimaryLabel("D8")).toBe("Spatial differentiation check");
    expect(publicPrimaryLabel("q_A")).toBe("Historical position");
    expect(publicPrimaryLabel("historical quantile position")).toBe(
      "Historical position",
    );
    expect(publicPrimaryLabel("S")).toBe("Observed separation across zones");
    expect(publicPrimaryLabel("Decision 8 floor")).toBe(
      "Minimum separation required by the analysis policy",
    );
    expect(publicPrimaryLabel("FULL_REFERENCE")).toBe(
      "Historical reference available",
    );
    expect(publicPrimaryLabel("INSUFFICIENT_EVIDENCE")).toBe(
      "Not enough spatial differentiation to support ordering",
    );
    expect(PUBLIC_SENTENCE.INSUFFICIENT_EVIDENCE).toBe(
      "Not enough spatial differentiation to support ordering",
    );
  });

  it("never shows ZoneFeatureVector", () => {
    expect(neverShow("ZoneFeatureVector")).toBe(true);
    expect(publicPrimaryLabel("ZoneFeatureVector")).toBeNull();
    expect(technicalDetailsLabel("ZoneFeatureVector")).toBeNull();
    expect(lookup("ZoneFeatureVector")?.surface).toBe("never");
  });

  it("keeps Evidence DAG / GRAPH_POPULATED in methodology only", () => {
    expect(publicPrimaryLabel("GRAPH_POPULATED")).toBeNull();
    expect(publicPrimaryLabel("Evidence DAG")).toBeNull();
    expect(technicalDetailsLabel("GRAPH_POPULATED")).toBe("Evidence lineage");
    expect(lookup("GRAPH_POPULATED")?.surface).toBe("technical_details");
  });

  it("removes INTERVENTION PRIORITY and bare READY", () => {
    expect(removeFromPrimary("INTERVENTION PRIORITY")).toBe(true);
    expect(publicPrimaryLabel("INTERVENTION PRIORITY")).toBeNull();
    expect(
      publicPrimaryLabel(
        "CONTEXTUAL PREPAREDNESS PRIORITY — THERMAL DIFFERENTIATION UNAVAILABLE",
      ),
    ).toBeNull();
    expect(removeFromPrimary("READY")).toBe(true);
    expect(publicPrimaryLabel("READY")).toBeNull();
    expect(canonicalPublicStatus("READY")).toBeNull();
  });

  it("does not invent statuses outside the preferred set", () => {
    expect(PUBLIC_STATUSES).toEqual([
      "ANALYSIS COMPLETE",
      "SPATIAL ORDERING SUPPORTED",
      "SPATIAL ORDERING WITHHELD",
      "HISTORICAL REFERENCE AVAILABLE",
      "SNAPSHOT UNAVAILABLE",
      "REPLAY EVIDENCE",
    ]);
    expect(PUBLIC_STATUSES).not.toContain("READY");
    expect(PUBLIC_STATUSES).not.toContain("INSUFFICIENT EVIDENCE");
  });

  it("maps READY only through context", () => {
    expect(publicStatusForReady("ranking_permitted")).toBe(
      PUBLIC_STATUS.SPATIAL_ORDERING_SUPPORTED,
    );
    expect(publicStatusForReady("ranking_withheld")).toBe(
      PUBLIC_STATUS.SPATIAL_ORDERING_WITHHELD,
    );
    expect(publicStatusForReady("job_complete")).toBe(
      PUBLIC_STATUS.ANALYSIS_COMPLETE,
    );
    expect(publicStatusForReady("historical_reference")).toBe(
      PUBLIC_STATUS.HISTORICAL_REFERENCE_AVAILABLE,
    );
    expect(publicStatusForReady("snapshot_unavailable")).toBe(
      PUBLIC_STATUS.SNAPSHOT_UNAVAILABLE,
    );
    expect(publicStatusForReady("source_replay")).toBe(
      PUBLIC_STATUS.REPLAY_EVIDENCE,
    );
    expect(publicStatusForRankingState("READY")).toBe(
      PUBLIC_STATUS.SPATIAL_ORDERING_SUPPORTED,
    );
    expect(publicStatusForRankingState("INSUFFICIENT_EVIDENCE")).toBe(
      PUBLIC_STATUS.SPATIAL_ORDERING_WITHHELD,
    );
  });

  it("shows backend order only when ordering is allowed and useful", () => {
    expect(
      relativeOrderLabel({ orderingAllowed: false, useful: true, order: 1, of: 25 }),
    ).toBeNull();
    expect(
      relativeOrderLabel({ orderingAllowed: true, useful: false, order: 1, of: 25 }),
    ).toBeNull();
    expect(
      relativeOrderLabel({ orderingAllowed: true, useful: true, order: 4, of: 25 }),
    ).toBe("Relative order 4 of 25 within this analysis");
    expect(relativeOrderLabel({ orderingAllowed: true, useful: true })).toBe(
      PUBLIC_NOUN.BACKEND_ORDER,
    );
    expect(publicPrimaryLabel("backend_order")).toBeNull();
  });

  it("keeps shipped ORDER SHOWN / ORDER WITHHELD as aliases, not new statuses", () => {
    expect(SHIPPED_ALIAS.ORDER_SHOWN).toBe("ORDER SHOWN");
    expect(SHIPPED_ALIAS.ORDER_WITHHELD).toBe("ORDER WITHHELD");
    expect(
      shippedAliasForPublicStatus(PUBLIC_STATUS.SPATIAL_ORDERING_SUPPORTED),
    ).toBe("ORDER SHOWN");
    expect(
      shippedAliasForPublicStatus(PUBLIC_STATUS.SPATIAL_ORDERING_WITHHELD),
    ).toBe("ORDER WITHHELD");
    expect(
      shippedAliasForPublicStatus(PUBLIC_STATUS.ANALYSIS_COMPLETE),
    ).toBeNull();
  });

  it("maps common backend aliases without changing math tokens", () => {
    expect(canonicalPublicStatus("SUFFICIENT")).toBe(
      PUBLIC_STATUS.SPATIAL_ORDERING_SUPPORTED,
    );
    expect(canonicalPublicStatus("D8_INSUFFICIENT")).toBe(
      PUBLIC_STATUS.SPATIAL_ORDERING_WITHHELD,
    );
    expect(
      canonicalPublicStatus("THERMAL_SPATIAL_DIFFERENTIATION_INSUFFICIENT"),
    ).toBe(PUBLIC_STATUS.SPATIAL_ORDERING_WITHHELD);
    expect(canonicalPublicStatus("FULL_REFERENCE")).toBe(
      PUBLIC_STATUS.HISTORICAL_REFERENCE_AVAILABLE,
    );
    expect(canonicalPublicStatus("complete")).toBe(
      PUBLIC_STATUS.ANALYSIS_COMPLETE,
    );
    expect(canonicalPublicStatus("replay")).toBe(PUBLIC_STATUS.REPLAY_EVIDENCE);
    expect(canonicalPublicStatus("NOT ON THIS SURFACE")).toBe(
      PUBLIC_STATUS.SNAPSHOT_UNAVAILABLE,
    );
  });

  it("forbids backend tokens as primary stamps", () => {
    const required = [
      "READY",
      "INTERVENTION PRIORITY",
      "ZoneFeatureVector",
      "GRAPH_POPULATED",
      "INSUFFICIENT_EVIDENCE",
      "FULL_REFERENCE",
      "q_A",
      "Decision 8",
      "backend_order",
    ];
    for (const term of required) {
      expect(FORBIDDEN_PRIMARY_TERMS).toContain(term);
    }
    expect(
      chromeUsesForbiddenPrimary("ORDER SHOWN", "READY"),
    ).toBe(false);
    expect(chromeUsesForbiddenPrimary("READY", "READY")).toBe(true);
    expect(
      chromeUsesForbiddenPrimary(
        "Rank is not a probability and not a heat-severity class.",
        "probability",
      ),
    ).toBe(false);
  });

  it("records scan notes for unsupported claim words", () => {
    const terms = SCAN_NOTES.map((row) => row.term);
    expect(terms).toEqual([
      "intervention priority",
      "priority",
      "risk",
      "danger",
      "probability",
      "real-time",
      "current",
      "city-wide",
      "forecast",
      "overnight",
      "recovery",
      "WBGT",
      "HeatDose",
    ]);
    expect(SCAN_NOTES.find((row) => row.term === "danger")?.verdict).toBe(
      "absent",
    );
    expect(
      SCAN_NOTES.find((row) => row.term === "intervention priority")?.verdict,
    ).toBe("remove");
    expect(QUALIFIED_CAPABILITY_NOUNS).toContain("HeatDose");
    expect(QUALIFIED_CAPABILITY_NOUNS).toContain("WBGT");
    expect(FORBIDDEN_CLAIM_PHRASES).toContain("overnight recovery");
    expect(FORBIDDEN_CLAIM_PHRASES).toContain("city-wide");
  });

  it("does not drop auditability — every required token has a row", () => {
    const internals = DICTIONARY.map((row) => row.internal);
    expect(internals).toEqual(
      expect.arrayContaining([
        "Decision 8",
        "q_A",
        "S",
        "Decision 8 floor",
        "FULL_REFERENCE",
        "INSUFFICIENT_EVIDENCE",
        "ZoneFeatureVector",
        "GRAPH_POPULATED",
        "INTERVENTION PRIORITY",
        "backend order",
        "READY",
      ]),
    );
  });
});
