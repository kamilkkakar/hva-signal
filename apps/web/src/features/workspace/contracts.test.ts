import { readFileSync } from "node:fs";
import path from "node:path";
import { fileURLToPath } from "node:url";
import { describe, expect, it } from "vitest";

const here = path.dirname(fileURLToPath(import.meta.url));

function readSrc(relPath: string): string {
  return readFileSync(path.resolve(here, relPath), "utf8");
}

describe("workspace contracts", () => {
  it("App.tsx renders Workspace (not JudgeShell directly)", () => {
    const app = readSrc("../../app/App.tsx");
    expect(app).toContain("Workspace");
    expect(app).not.toContain("PlaceSearch");
    expect(app.toLowerCase()).not.toMatch(/log in|login|sign up|signup|oauth/);
  });

  it("header does not contain CACHED DEMONSTRATION", () => {
    const header = readSrc("./WorkspaceHeader.tsx");
    expect(header).not.toContain("CACHED");
    expect(header).not.toContain("Cached demonstration");
    expect(header).not.toContain("Cached Demonstration");
  });

  it("header does not hardcode Phoenix or area count", () => {
    const header = readSrc("./WorkspaceHeader.tsx");
    expect(header).not.toContain("Phoenix · 25");
    expect(header).not.toContain("25 analysis areas");
  });

  it("workspace has Explore City and Compare Cities modes", () => {
    const ws = readSrc("./Workspace.tsx");
    expect(ws).toContain("ExploreCity");
    expect(ws).toContain("CompareCities");
  });

  it("ZonePanel uses Zone as public term", () => {
    const panel = readSrc("./ZonePanel.tsx");
    expect(panel).toContain("Zone");
    expect(panel).toContain("zone-name");
  });

  it("methods disclosure is closed by default", () => {
    const panel = readSrc("./ZonePanel.tsx");
    expect(panel).toContain("<details");
    expect(panel).toContain("Methods");
    expect(panel).toContain("Comparison-mode context uses published cross-city metrics");
  });

  it("ExploreCity has four-city support", () => {
    const explore = readSrc("./ExploreCity.tsx");
    expect(explore).toContain("cross-city");
    expect(explore).toContain("cityGeometry");
    expect(explore).toContain("publishedCrossCityCatalog");
    expect(explore).toContain("activeCrossCityCatalog");
  });

  it("live integration calls POST endpoint only on explicit Run", () => {
    const explore = readSrc("./ExploreCity.tsx");
    expect(explore).toContain("/api/v1/live/selected-time");
    expect(explore).toContain("POST");
    const controls = readSrc("./CityControls.tsx");
    expect(controls).toContain("Run observation");
  });

  it("CityControls stays fail-closed unless its caller explicitly enables live", () => {
    const controls = readSrc("./CityControls.tsx");
    expect(controls).toContain("liveAvailable = false");
    expect(controls).toContain("observation-published-only");
    expect(controls).toContain("ws-published-badge");
    const explore = readSrc("./ExploreCity.tsx");
    expect(explore).toContain("liveAvailable");
  });

  it("no FortyGuard API key in workspace source", () => {
    const files = [
      readSrc("./Workspace.tsx"),
      readSrc("./ExploreCity.tsx"),
      readSrc("./CityControls.tsx"),
      readSrc("./ZonePanel.tsx"),
      readSrc("./WorkspaceHeader.tsx"),
    ];
    for (const content of files) {
      expect(content.toLowerCase()).not.toContain("fortyguard_api_key");
      expect(content.toLowerCase()).not.toContain("api_key");
    }
  });

  it("HVA story rail and outlook panel exist", () => {
    const rail = readSrc("./HvaStoryRail.tsx");
    const outlook = readSrc("./OutlookPanel.tsx");
    expect(rail).toContain("hva-story-rail");
    expect(rail).toContain("hva-stage-heat");
    expect(outlook).toContain("hva-outlook-panel");
    expect(outlook).toContain("What to watch next");
    expect(outlook).toContain("Forecast remains blocked");
    expect(outlook).toContain("Forecast contract");
  });

  it("action engine caps at 3 evidence-linked actions", () => {
    const engine = readSrc("./actionEngine.ts");
    expect(engine).toContain("whyShown");
    expect(engine).toContain(">= 3");
  });

  it("features the strongest matched-night evidence while keeping secondary evidence progressive", () => {
    const evidence = readSrc("./CityEvidenceSections.tsx");
    const detailsCount = (evidence.match(/<details className="ws-analysis-section"/g) || []).length;
    expect(detailsCount).toBeGreaterThanOrEqual(2);
    expect(evidence).toContain("ws-analysis-section-featured");
    expect(evidence).toContain("matched-night-section");
    expect(evidence).toContain("cityEvidenceCapabilities");
    expect(evidence).not.toMatch(/if\s*\(\s*city\s*===\s*["']phoenix/i);
    const explore = readSrc("./ExploreCity.tsx");
    expect(explore).toContain("CityEvidenceSections");
    expect(explore).toContain("ws-map-column");
  });

  it("inventory/methods are behind disclosure not primary surface", () => {
    const panel = readSrc("./ZonePanel.tsx");
    expect(panel).toContain("<details");
    expect(panel).not.toContain("Development ledger");
    expect(panel).not.toContain("roadmap");
  });

  it("general vendor stays OFF in workspace source", () => {
    const explore = readSrc("./ExploreCity.tsx");
    expect(explore).not.toContain("GENERAL_VENDOR");
    expect(explore).not.toContain("general_vendor");
  });

  it("cross-city comparison is first-class mode", () => {
    const compare = readSrc("./CompareCities.tsx");
    expect(compare).toContain("CrossCitySection");
  });

  it("workspace CSS provides 70/30 map layout", () => {
    const css = readFileSync(path.resolve(here, "./workspace.css"), "utf8");
    expect(css).toContain("ws-explore-main");
    expect(css).toContain("22rem");
    expect(css).toContain("ws-map-column");
  });

  it("spatial gate uses a stable unavailable label when not loading", () => {
    const explore = readSrc("./ExploreCity.tsx");
    expect(explore).toContain("Spatial comparison status unavailable");
    expect(explore).toContain("snapshot?.result == null || submitting");
  });

  it("zone panel can show older housing", () => {
    const panel = readSrc("./ZonePanel.tsx");
    expect(panel).toContain("Older housing");
    expect(panel).toContain("olderHousingPct");
  });

  it("context cards separate value and label blocks", () => {
    const panel = readSrc("../experience/ContextPanel.tsx");
    const css = readFileSync(path.resolve(here, "../experience/experience.css"), "utf8");
    expect(panel).toContain("hx-card-stack");
    expect(css).toContain(".hx-card-stack");
    expect(css).toContain("text-transform: uppercase");
  });
});
