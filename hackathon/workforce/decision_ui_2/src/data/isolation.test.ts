import { readFileSync, readdirSync, statSync } from "node:fs";
import path from "node:path";
import { fileURLToPath } from "node:url";
import { describe, expect, it } from "vitest";

const SRC = path.resolve(path.dirname(fileURLToPath(import.meta.url)), "..");

function walk(dir: string): string[] {
  return readdirSync(dir).flatMap((entry) => {
    const full = path.join(dir, entry);
    const stat = statSync(full);
    if (stat.isDirectory()) {
      if (entry === "fixtures" || entry === "test") {
        return [];
      }
      return walk(full);
    }
    if (/\.test\.(ts|tsx)$/.test(entry)) {
      return [];
    }
    if (/\.(ts|tsx)$/.test(entry)) {
      return [full];
    }
    return [];
  });
}

describe("production isolation", () => {
  it("does not import test-only fixtures from production modules", () => {
    const files = walk(SRC);
    expect(files.length).toBeGreaterThan(10);
    for (const file of files) {
      const source = readFileSync(file, "utf8");
      expect(source, file).not.toMatch(/from ["']@\/fixtures/);
      expect(source, file).not.toMatch(/from ["']\.\.\/fixtures/);
      expect(source, file).not.toMatch(/TEST_ONLY_STORY_CARD|TEST_ONLY_HOURLY|TEST_ONLY_AREAS/);
    }
  });
});
