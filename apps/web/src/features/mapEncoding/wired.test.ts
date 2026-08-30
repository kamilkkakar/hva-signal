import { readFileSync } from "node:fs";
import { dirname, join } from "node:path";
import { fileURLToPath } from "node:url";
import { describe, expect, it } from "vitest";

describe("Judge map encoding wire", () => {
  it("uses mapEncoding tokens on the JudgeMap host", () => {
    const source = readFileSync(
      join(
        dirname(fileURLToPath(import.meta.url)),
        "..",
        "mapInteraction",
        "highlight.ts",
      ),
      "utf8",
    );
    expect(source).toContain("signalAFillPaint");
    expect(source).toContain("signalALinePaint");
    expect(source).not.toContain("#2f8f78");
    expect(source).not.toContain("#d56a1c");
    expect(source).not.toMatch(/FORTYGUARD/);
  });
});
