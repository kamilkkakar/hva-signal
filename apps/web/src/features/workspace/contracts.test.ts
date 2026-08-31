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
  });

  it("ExploreCity has four-city support", () => {
    const explore = readSrc("./ExploreCity.tsx");
    expect(explore).toContain("cross-city");
    expect(explore).toContain("cityGeometry");
    expect(explore).toContain("crossCityCatalog");
  });

  it("live integration calls POST endpoint only on explicit Run", () => {
    const explore = readSrc("./ExploreCity.tsx");
    expect(explore).toContain("/api/v1/live/selected-time");
    expect(explore).toContain("POST");
    const controls = readSrc("./CityControls.tsx");
    expect(controls).toContain("Run observation");
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

  it("below-map sections are collapsed by default", () => {
    const explore = readSrc("./ExploreCity.tsx");
    const detailsCount = (explore.match(/<details className="ws-analysis-section"/g) || []).length;
    expect(detailsCount).toBeGreaterThanOrEqual(3);
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
  });
});
