import { readFileSync } from "node:fs";
import path from "node:path";
import { fileURLToPath } from "node:url";
import { describe, expect, it } from "vitest";

const here = path.dirname(fileURLToPath(import.meta.url));
const QUERY_RAIL = readFileSync(path.join(here, "QueryRail.tsx"), "utf8").replace(
  /\s+/g,
  " ",
);

describe("QueryRail claim-safe copy", () => {
  it("names phoenix-demo, not Phoenix-as-city shorthand (R4)", () => {
    expect(QUERY_RAIL).toContain("phoenix-demo 03:00");
    expect(QUERY_RAIL).not.toMatch(/Phoenix 03:00/);
    expect(QUERY_RAIL).toContain("Not Census-place national Phoenix, AZ");
  });

  it("does not invite ranking, 100 m targeting, or current conditions", () => {
    expect(QUERY_RAIL.toLowerCase()).not.toContain("why a zone ranks");
    expect(QUERY_RAIL).toContain("not 100 m targeting");
    expect(QUERY_RAIL).toContain("Not current conditions");
    expect(QUERY_RAIL).toContain("does not authorize spend");
    expect(QUERY_RAIL).toContain('placeholder="Copilot is locked."');
  });
});
