import { readFileSync, readdirSync } from "node:fs";
import path from "node:path";
import { fileURLToPath } from "node:url";
import { describe, expect, it } from "vitest";
import { FORBIDDEN_FIRST_READ } from "./copy";

const here = path.dirname(fileURLToPath(import.meta.url));

function collect(dir: string): string {
  return readdirSync(dir)
    .filter((name) => name.endsWith(".tsx"))
    .map((name) => readFileSync(path.join(dir, name), "utf8"))
    .join("\n");
}

describe("experience first-read surface", () => {
  const source = collect(here);

  it("does not print method tokens in first-read product copy", () => {
    expect(source).not.toContain("NOT REQUESTED");
    expect(source).not.toContain("AWAITING ANALYSIS");
    expect(source).not.toContain("24-HOUR CURVE");
    expect(source).not.toMatch(/climate trend/i);
    expect(source).not.toContain("q_A =");
    expect(source).not.toContain("NO COOLING SITE");
    for (const token of FORBIDDEN_FIRST_READ) {
      if (token === "q_A" || token === "Decision 8") {
        continue;
      }
      expect(source).not.toContain(token);
    }
  });

  it("keeps FortyGuard on the thermal badge, not as a live vendor claim", () => {
    expect(source).toContain("BADGE_PROVIDER");
    expect(readFileSync(path.join(here, "copy.ts"), "utf8")).toContain("FortyGuard · 100 m TCM");
    expect(source).not.toContain("FORTYGUARD LIVE");
    expect(source).not.toContain("FORTYGUARD CACHED");
  });

  it("does not combine thermal, context, and preparedness into a score", () => {
    expect(source).not.toMatch(/vulnerability score/i);
    expect(source).not.toMatch(/combined score/i);
    expect(source).not.toMatch(/heat-risk/i);
  });
});
