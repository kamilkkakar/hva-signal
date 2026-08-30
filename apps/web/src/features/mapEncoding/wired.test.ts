import { readFileSync } from "node:fs";
import { dirname, join } from "node:path";
import { fileURLToPath } from "node:url";
import { describe, expect, it } from "vitest";

describe("MapStage encoding wire", () => {
  it("uses mapEncoding tokens instead of phosphor-filament", () => {
    const source = readFileSync(
      join(dirname(fileURLToPath(import.meta.url)), "..", "map", "MapStage.tsx"),
      "utf8",
    );
    expect(source).toContain("signalAFillPaint");
    expect(source).toContain("HistoricalPositionLegend");
    expect(source).toContain("allHatchImages");
    expect(source).not.toContain("#2f8f78");
    expect(source).not.toContain("#d56a1c");
    expect(source).not.toMatch(/FORTYGUARD/);
  });
});
