import { readFileSync } from "node:fs";
import path from "node:path";
import { fileURLToPath } from "node:url";
import { describe, expect, it } from "vitest";
import { gatedPlaceSearchLanding, isPlaceSearchApiEnabled, isPlaceSearchEnabled } from "./flags";

const here = path.dirname(fileURLToPath(import.meta.url));

describe("place search feature flags", () => {
  it("defaults OFF so phoenix-demo remains the landing product", () => {
    expect(isPlaceSearchEnabled()).toBe(false);
    expect(isPlaceSearchApiEnabled()).toBe(false);
    expect(gatedPlaceSearchLanding("#/")).toBe("phoenix-demo");
    expect(gatedPlaceSearchLanding("#/phoenix-demo")).toBe("phoenix-demo");
  });

  it("keeps App landing on CommandCenterShell (phoenix-demo) with no login", () => {
    const app = readFileSync(path.resolve(here, "../../app/App.tsx"), "utf8");
    expect(app).toContain("CommandCenterShell");
    expect(app).not.toContain("PlaceSearch");
    expect(app.toLowerCase()).not.toMatch(/log in|login|sign up|signup|oauth/);
  });
});
