import { readFileSync, readdirSync } from "node:fs";
import { dirname, join } from "node:path";
import { fileURLToPath } from "node:url";
import { describe, expect, it } from "vitest";

const root = dirname(fileURLToPath(import.meta.url));

function implementationFiles(): string[] {
  const found: string[] = [];
  const walk = (dir: string) => {
    for (const entry of readdirSync(dir, { withFileTypes: true })) {
      if (entry.name.endsWith(".test.ts")) {
        continue;
      }
      const path = join(dir, entry.name);
      if (entry.isDirectory()) {
        walk(path);
        continue;
      }
      if (/\.(ts|tsx)$/.test(entry.name)) {
        found.push(path);
      }
    }
  };
  walk(root);
  return found;
}

describe("productStory isolation", () => {
  it("does not stitch into JudgeShell or enable public B / search / geo", () => {
    const files = implementationFiles();
    expect(files.length).toBeGreaterThan(2);
    for (const path of files) {
      const source = readFileSync(path, "utf8");
      expect(source, path).not.toMatch(/features\/judgeShell/);
      expect(source, path).not.toMatch(/JudgeShell/);
      expect(source, path).not.toMatch(/PUBLIC_SIGNAL_B\s*=\s*true/);
      expect(source, path).not.toMatch(/\bfetch\s*\(/);
      expect(source, path).not.toMatch(/FORTYGUARD/);
      expect(source, path).not.toMatch(/FortyGuard live/);
      expect(source, path).not.toContain(
        "Selected-hour snapshot is not published here.",
      );
    }
  });
});
