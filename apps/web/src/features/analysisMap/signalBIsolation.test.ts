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

describe("Signal B map isolation", () => {
  it("does not reuse the A rank machine or stretch encodings", () => {
    const files = implementationFiles();
    expect(files.length).toBeGreaterThan(5);
    for (const path of files) {
      const source = readFileSync(path, "utf8");
      expect(source, path).not.toMatch(/INTERVENTION PRIORITY/);
      expect(source, path).not.toMatch(/CONTEXTUAL PREPAREDNESS/);
      expect(source, path).not.toMatch(/backend_order/);
      expect(source, path).not.toMatch(/\bq_A\s*[:=]/);
      expect(source, path).not.toMatch(/["']q_A["']/);
      expect(source, path).not.toMatch(/rankingPresentation/);
      expect(source, path).not.toMatch(/mapLayerFromLimitations/);
      expect(source, path).not.toMatch(/mapPresentationFromBind/);
      expect(source, path).not.toMatch(/#2f8f78/);
      expect(source, path).not.toMatch(/#d56a1c/);
      expect(source, path).not.toMatch(/LITTLE SPATIAL THERMAL CONTRAST/);
      expect(source, path).not.toMatch(/Priority map/);
      expect(source, path).not.toMatch(/\binterpolate\b/);
    }
  });
});
