import { readFileSync, readdirSync } from "node:fs";
import path from "node:path";
import { fileURLToPath } from "node:url";
import { describe, expect, it } from "vitest";

const here = path.dirname(fileURLToPath(import.meta.url));

function collectSource(): string {
  return readdirSync(here)
    .filter((name) => /\.(tsx|ts|css)$/.test(name) && !name.endsWith(".test.ts"))
    .map((name) => readFileSync(path.join(here, name), "utf8"))
    .join("\n");
}

describe("judge shell kill list", () => {
  const source = collectSource();

  it("does not mount the 3-col novels, fake timeline, or locked Copilot", () => {
    expect(source).not.toContain("TimelineBar");
    expect(source).not.toContain("QueryRail");
    expect(source).not.toContain("DecisionRail");
    expect(source).not.toContain("SourceTape");
    expect(source).not.toContain("CommandCenterShell");
    expect(source).not.toMatch(/Copilot is locked/);
    expect(source).not.toContain("Current / Forecast / Scenario / Overnight");
    expect(source).not.toMatch(/["']Current["']/);
    expect(source).not.toMatch(/["']Forecast["']/);
    expect(source).not.toMatch(/["']Scenario["']/);
    expect(source).not.toMatch(/["']Overnight["']/);
  });

  it("does not keep the permanent 260 / flex / 300 grid", () => {
    expect(source).not.toContain("shell-grid");
    expect(source).not.toMatch(/260px\s+1fr\s+300px/);
    expect(source).toContain("judge-shell");
  });

  it("does not name FortyGuard on the judge surface", () => {
    const surface = readdirSync(here)
      .filter((name) => /\.(tsx|css)$/.test(name))
      .map((name) => readFileSync(path.join(here, name), "utf8"))
      .join("\n");
    expect(surface.toLowerCase()).not.toContain("fortyguard");
  });

  it("keeps overflow-safe bands without hiding page scroll", () => {
    const css = readFileSync(path.join(here, "judgeShell.css"), "utf8");
    expect(css).toContain("min-width: 0");
    expect(css).toContain("max-width: 100%");
    expect(css).toContain("overflow-wrap: anywhere");
    expect(css).toContain("flex-wrap: wrap");
    expect(css).not.toMatch(/\.judge-shell\s*\{[^}]*overflow-x:\s*hidden/s);
  });
});
