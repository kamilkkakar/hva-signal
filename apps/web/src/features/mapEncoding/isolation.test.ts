import { readFileSync, readdirSync } from "node:fs";
import { dirname, join } from "node:path";
import { fileURLToPath } from "node:url";
import { describe, expect, it } from "vitest";
import { SIGNAL_B_PUBLIC } from "./tokens";

const root = dirname(fileURLToPath(import.meta.url));

function implementationFiles(): string[] {
  const found: string[] = [];
  for (const entry of readdirSync(root, { withFileTypes: true })) {
    if (entry.name.endsWith(".test.ts")) {
      continue;
    }
    if (/\.(ts|tsx|css)$/.test(entry.name)) {
      found.push(join(root, entry.name));
    }
  }
  return found;
}

describe("map encoding isolation", () => {
  it("does not enable public B, fetch a vendor, or keep the rejected ramp", () => {
    expect(SIGNAL_B_PUBLIC).toBe(false);
    const files = implementationFiles();
    expect(files.length).toBeGreaterThan(6);
    for (const path of files) {
      const source = readFileSync(path, "utf8");
      expect(source, path).not.toMatch(/FORTYGUARD/);
      expect(source, path).not.toMatch(/FortyGuard/);
      expect(source, path).not.toMatch(/\bfetch\s*\(/);
      expect(source, path).not.toMatch(/#2f8f78/);
      expect(source, path).not.toMatch(/#d56a1c/);
      expect(source, path).not.toMatch(/INTERVENTION PRIORITY/);
      expect(source, path).not.toMatch(/safe\s*↔\s*danger/i);
      expect(source, path).not.toMatch(/SIGNAL_B_NEUTRAL_MAP_ENABLED\s*=\s*true/);
    }
  });
});
