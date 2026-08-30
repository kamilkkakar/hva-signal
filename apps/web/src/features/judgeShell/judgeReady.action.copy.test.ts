import { existsSync, readFileSync } from "node:fs";
import path from "node:path";
import { fileURLToPath, pathToFileURL } from "node:url";
import { describe, expect, it } from "vitest";

const here = path.dirname(fileURLToPath(import.meta.url));
const fixturePath = path.resolve(
  here,
  "../../../e2e/fixtures/action-framing.json",
);

const framing = JSON.parse(readFileSync(fixturePath, "utf8")) as {
  status: string;
  scope: string;
  title: string;
  required_context: string;
  sufficient: {
    stamp: string;
    says: string;
    supports: string;
    does_not: string;
  };
  insufficient: {
    stamp: string;
    says: string;
    supports: string;
    does_not: string;
  };
  forbidden_phrases: string[];
};

type ActionCopyModule = {
  SUFFICIENT_STAMP?: string;
  INSUFFICIENT_STAMP?: string;
  SUFFICIENT_SAYS_COPY?: string;
  SUFFICIENT_SUPPORTS_COPY?: string;
  SUFFICIENT_DOES_NOT_COPY?: string;
  INSUFFICIENT_SAYS_COPY?: string;
  INSUFFICIENT_SUPPORTS_COPY?: string;
  INSUFFICIENT_DOES_NOT_COPY?: string;
  REQUIRED_CONTEXT_COPY?: string;
  ACTION_V0_STATUS?: string;
  ACTION_V0_SCOPE?: string;
  publishedActionCopy?: () => string[];
};

async function loadActionCopy(): Promise<ActionCopyModule | null> {
  const candidates = [
    path.resolve(here, "action/copy.ts"),
    path.resolve(here, "../action/copy.ts"),
  ];
  for (const file of candidates) {
    if (!existsSync(file)) {
      continue;
    }
    return (await import(pathToFileURL(file).href)) as ActionCopyModule;
  }
  return null;
}

describe("judgeShell Action framing copy", () => {
  it("pins sufficient 2022-06-30 framing as one input, not deployment", () => {
    expect(framing.sufficient.stamp).toBe("SUPPORTS SPATIAL ORDERING");
    expect(framing.sufficient.says).toContain("supports spatial ordering");
    expect(framing.sufficient.says).toContain("frozen historical signal protocol");
    expect(framing.sufficient.supports).toContain("one input");
    expect(framing.sufficient.does_not).toContain(
      "does not authorize automatic deployment",
    );
    expect(framing.sufficient.does_not).toContain(framing.required_context);
  });

  it("pins insufficient 2022-07-01 framing as withhold, not all-clear", () => {
    expect(framing.insufficient.stamp).toBe("DO NOT USE THERMAL RANKING ALONE");
    expect(framing.insufficient.says).toContain(
      "does not support a defensible spatial ordering",
    );
    expect(framing.insufficient.supports).toBe(
      "Do not use thermal ranking alone for zone prioritization.",
    );
    expect(framing.insufficient.does_not).toContain("not a safety clearance");
    expect(framing.insufficient.does_not).toContain(
      "does not mean zones have equal need",
    );
    expect(framing.insufficient.does_not).toContain(framing.required_context);
  });

  it("requires remaining context and forbids efficacy language", () => {
    const blob = [
      framing.status,
      framing.scope,
      framing.title,
      framing.required_context,
      framing.sufficient.says,
      framing.sufficient.supports,
      framing.sufficient.does_not,
      framing.insufficient.says,
      framing.insufficient.supports,
      framing.insufficient.does_not,
    ]
      .join("\n")
      .toLowerCase();
    expect(blob).toContain("vulnerability");
    expect(blob).toContain("preparedness");
    expect(blob).toContain("operational constraints");
    expect(blob).toContain("local context");
    expect(blob).not.toMatch(/%/);
    expect(blob).not.toContain("fortyguard");
    expect(blob).not.toContain("q_a");
    for (const phrase of framing.forbidden_phrases) {
      expect(blob.includes(phrase), phrase).toBe(false);
    }
  });

  it("matches mounted judgeShell/action copy when that module is present", async () => {
    const copy = await loadActionCopy();
    if (!copy) {
      expect(existsSync(fixturePath)).toBe(true);
      return;
    }
    expect(copy.SUFFICIENT_STAMP).toBe(framing.sufficient.stamp);
    expect(copy.INSUFFICIENT_STAMP).toBe(framing.insufficient.stamp);
    expect(copy.SUFFICIENT_SAYS_COPY).toBe(framing.sufficient.says);
    expect(copy.SUFFICIENT_SUPPORTS_COPY).toBe(framing.sufficient.supports);
    expect(copy.SUFFICIENT_DOES_NOT_COPY).toBe(framing.sufficient.does_not);
    expect(copy.INSUFFICIENT_SAYS_COPY).toBe(framing.insufficient.says);
    expect(copy.INSUFFICIENT_SUPPORTS_COPY).toBe(framing.insufficient.supports);
    expect(copy.INSUFFICIENT_DOES_NOT_COPY).toBe(framing.insufficient.does_not);
    expect(copy.REQUIRED_CONTEXT_COPY).toBe(framing.required_context);
    expect(copy.ACTION_V0_STATUS).toBe(framing.status);
    expect(copy.ACTION_V0_SCOPE).toBe(framing.scope);
    if (copy.publishedActionCopy) {
      const published = copy.publishedActionCopy().join("\n").toLowerCase();
      expect(published).not.toContain("fortyguard");
    }
  });
});
