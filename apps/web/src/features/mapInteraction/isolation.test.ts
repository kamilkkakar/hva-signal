import { readFileSync, readdirSync } from "node:fs";
import { dirname, join } from "node:path";
import { fileURLToPath } from "node:url";
import { describe, expect, it } from "vitest";

const root = dirname(fileURLToPath(import.meta.url));

function implementationFiles(): string[] {
  const skip = new Set(["node_modules"]);
  const found: string[] = [];
  const walk = (dir: string) => {
    for (const entry of readdirSync(dir, { withFileTypes: true })) {
      if (skip.has(entry.name) || entry.name.endsWith(".test.ts")) {
        continue;
      }
      const path = join(dir, entry.name);
      if (entry.isDirectory()) {
        walk(path);
        continue;
      }
      if (/\.(ts|tsx|css)$/.test(entry.name)) {
        found.push(path);
      }
    }
  };
  walk(root);
  return found;
}

describe("map interaction isolation", () => {
  it("does not restyle CommandCenter, invent an A ramp, or name a private vendor in chrome", () => {
    const files = implementationFiles();
    expect(files.length).toBeGreaterThan(8);
    for (const path of files) {
      const source = readFileSync(path, "utf8");
      expect(source, path).not.toMatch(/CommandCenterShell/);
      expect(source, path).not.toMatch(/INTERVENTION PRIORITY/);
      expect(source, path).not.toMatch(/intervention_evidence/);
      expect(source, path).not.toMatch(/CONTEXTUAL PREPAREDNESS/);
      expect(source, path).not.toMatch(/harm probability/i);
      expect(source, path).not.toMatch(/backend order/i);
      expect(source, path).not.toMatch(/rankingPresentation/);
      expect(source, path).not.toMatch(/mapLayerFromLimitations/);
      expect(source, path).not.toMatch(/mapPresentationFromBind/);
      expect(source, path).not.toMatch(/#2f8f78/);
      expect(source, path).not.toMatch(/#d56a1c/);
      expect(source, path).not.toMatch(/FORTYGUARD/);
      expect(source, path).not.toMatch(/FortyGuard/);
      expect(source, path).not.toMatch(/\bfetch\s*\(/);
      expect(source, path).not.toMatch(/\binterpolate\b/);
    }
  });
});
