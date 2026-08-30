import { readFileSync, readdirSync } from "node:fs";
import { dirname, join } from "node:path";
import { fileURLToPath } from "node:url";
import { describe, expect, it } from "vitest";

const root = dirname(fileURLToPath(import.meta.url));

function implementationFiles(): string[] {
  const found: string[] = [];
  for (const entry of readdirSync(root, { withFileTypes: true })) {
    if (entry.name.endsWith(".test.ts")) {
      continue;
    }
    if (/\.(ts|tsx)$/.test(entry.name)) {
      found.push(join(root, entry.name));
    }
  }
  return found;
}

describe("judgeShell/map isolation", () => {
  it("does not host B on A, invent an A ramp, or name a private vendor", () => {
    const files = implementationFiles();
    expect(files.length).toBeGreaterThan(2);
    for (const path of files) {
      const source = readFileSync(path, "utf8");
      expect(source, path).not.toMatch(/CommandCenterShell/);
      expect(source, path).not.toMatch(/INTERVENTION PRIORITY/);
      expect(source, path).not.toMatch(/CONTEXTUAL PREPAREDNESS/);
      expect(source, path).not.toMatch(/#2f8f78/);
      expect(source, path).not.toMatch(/#d56a1c/);
      expect(source, path).not.toMatch(/FORTYGUARD/);
      expect(source, path).not.toMatch(/FortyGuard/);
      expect(source, path).not.toMatch(/\bfetch\s*\(/);
      expect(source, path).not.toMatch(/\binterpolate\b/);
    }
  });
});
