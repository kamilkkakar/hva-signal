import { readFileSync } from "node:fs";
import path from "node:path";
import { fileURLToPath } from "node:url";
import { describe, expect, it } from "vitest";

const here = path.dirname(fileURLToPath(import.meta.url));

describe("map-primary analysis workspace", () => {
  it("uses compact query + large map instead of three equal columns", () => {
    const shell = readFileSync(path.join(here, "JudgeShell.tsx"), "utf8");
    const css = readFileSync(path.join(here, "judgeShell.css"), "utf8");
    const mapCss = readFileSync(
      path.join(here, "../mapInteraction/mapInteraction.css"),
      "utf8",
    );
    expect(shell).toMatch(/judge-explore/);
    expect(shell).toMatch(/<RunBand \/>/);
    expect(shell).toMatch(/<MapBand/);
    expect(shell).toMatch(/SelectedZoneBand/);
    expect(css).toMatch(/grid-template-columns:\s*minmax\(12\.75rem,\s*15\.25rem\)\s*minmax\(0,\s*1fr\)/);
    expect(css).toMatch(/min-height:\s*min\(52vh,\s*34rem\)/);
    expect(css).not.toMatch(/judge-explore[^{]*\{[^}]*repeat\(3/);
    expect(mapCss).toMatch(
      /grid-template-columns:\s*minmax\(0,\s*1fr\)\s*minmax\(0,\s*18\.75rem\)/,
    );
  });

  it("does not mount the production MapStage beside the interaction map", () => {
    const mapBand = readFileSync(path.join(here, "MapBand.tsx"), "utf8");
    expect(mapBand).toMatch(/JudgeMap/);
    expect(mapBand).not.toMatch(/MapStage/);
    expect(mapBand).toMatch(/data-layout="map-primary"/);
  });
});
