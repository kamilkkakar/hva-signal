import { createHash } from "node:crypto";
import { readdirSync, readFileSync } from "node:fs";
import { resolve } from "node:path";
import { describe, expect, it } from "vitest";

const SHOT_DIR = resolve(process.cwd(), "../../docs/judge-experience/screenshots");

const CANONICAL = [
  "phoenix-landing-1440x900.png",
  "phoenix-thermal-map.png",
  "phoenix-canopy-map.png",
  "phoenix-income-map.png",
  "phoenix-older-housing-map.png",
  "phoenix-zone-panel.png",
  "phoenix-matched-night.png",
  "phoenix-observed-instants.png",
  "phoenix-context.png",
  "phoenix-preparedness.png",
  "phoenix-direction.png",
  "phoenix-method-provenance.png",
  "phoenix-1024.png",
  "phoenix-mobile-390x844.png",
] as const;

describe("approved Phoenix screenshot contract", () => {
  it("keeps only the canonical PNG set beside APPROVED_SCREENSHOTS.md", () => {
    const files = readdirSync(SHOT_DIR);
    const pngs = files.filter((name) => name.endsWith(".png")).sort();
    expect(pngs).toEqual([...CANONICAL].sort());
    expect(files).toContain("APPROVED_SCREENSHOTS.md");
  });

  it("embeds a SHA256 for every canonical file in the manifest", () => {
    const manifest = readFileSync(resolve(SHOT_DIR, "APPROVED_SCREENSHOTS.md"), "utf8");
    for (const name of CANONICAL) {
      const bytes = readFileSync(resolve(SHOT_DIR, name));
      const sha = createHash("sha256").update(bytes).digest("hex");
      expect(manifest).toContain(name);
      expect(manifest).toContain(sha);
    }
  });

  it("does not leave stale numbered aliases in docs", () => {
    const docsRoot = resolve(process.cwd(), "../../docs");
    const walk = (dir: string): string[] => {
      const out: string[] = [];
      for (const entry of readdirSync(dir, { withFileTypes: true })) {
        const full = resolve(dir, entry.name);
        if (entry.isDirectory()) out.push(...walk(full));
        else if (entry.name.endsWith(".md")) out.push(full);
      }
      return out;
    };
    const stale = /(01-1440|1440x900-landing|1024-landing|mobile-390x844|broken-basemap|API KEY REQUIRED)/i;
    for (const path of walk(docsRoot)) {
      if (path.includes("APPROVED_SCREENSHOTS.md")) continue;
      const text = readFileSync(path, "utf8");
      expect(text, path).not.toMatch(stale);
    }
  });
});
