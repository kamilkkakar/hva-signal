import { readFileSync, readdirSync } from "node:fs";
import { dirname, join } from "node:path";
import { fileURLToPath } from "node:url";
import { describe, expect, it } from "vitest";

const root = dirname(fileURLToPath(import.meta.url));

function implementationFiles(): string[] {
  const found: string[] = [];
  for (const entry of readdirSync(root, { withFileTypes: true })) {
    if (entry.name.endsWith(".test.ts") || entry.name === "copy.ts") {
      continue;
    }
    if (/\.(ts|tsx|css)$/.test(entry.name)) {
      found.push(join(root, entry.name));
    }
  }
  return found;
}

describe("judgeShell/charts isolation", () => {
  it("does not call a vendor, invent a threshold, or color-code risk bands", () => {
    const files = implementationFiles();
    expect(files.length).toBeGreaterThan(6);
    for (const path of files) {
      const source = readFileSync(path, "utf8");
      expect(source, path).not.toMatch(/FortyGuard/);
      expect(source, path).not.toMatch(/FORTYGUARD/);
      expect(source, path).not.toMatch(/\bfetch\s*\(/);
      expect(source, path).not.toMatch(/\binterpolate\b/);
      expect(source, path).not.toMatch(/INTERVENTION PRIORITY/);
      expect(source, path).not.toMatch(/#2f8f78/);
      expect(source, path).not.toMatch(/#d56a1c/);
      expect(source, path).not.toContain("minimum_useful_spread");
    }
  });
});
