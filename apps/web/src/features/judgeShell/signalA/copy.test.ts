import { describe, expect, it } from "vitest";
import {
  FORBIDDEN_CHROME_METHOD,
  FORBIDDEN_JUDGE_PHRASES,
  chromeUsesForbiddenPhrase,
  METHOD_D8,
  METHOD_QA,
  METHOD_S,
  STAMP_HISTORY_NOT_PREPARED,
  STAMP_ORDER_SHOWN,
  STAMP_ORDER_WITHHELD,
  publishedChromeCopy,
  publishedMethodCopy,
} from "./copy";

describe("SIG-A copy lock", () => {
  it("pins the three judge stamps", () => {
    expect(STAMP_ORDER_SHOWN).toBe("SPATIAL ORDERING SUPPORTED");
    expect(STAMP_ORDER_WITHHELD).toBe("SPATIAL ORDERING WITHHELD");
    expect(STAMP_HISTORY_NOT_PREPARED).toBe("HISTORY NOT PREPARED");
    expect(STAMP_ORDER_WITHHELD).not.toBe(STAMP_HISTORY_NOT_PREPARED);
    expect(STAMP_ORDER_WITHHELD).not.toBe("INSUFFICIENT EVIDENCE");
  });

  it("keeps q_A, Decision 8, and S in Method only", () => {
    const chrome = publishedChromeCopy().join("\n");
    for (const token of FORBIDDEN_CHROME_METHOD) {
      expect(chrome.includes(token), token).toBe(false);
    }
    const method = publishedMethodCopy().join("\n");
    expect(method).toContain("q_A");
    expect(method).toContain("Decision 8");
    expect(method).toContain("D8");
    expect(METHOD_QA).toContain("q_A");
    expect(METHOD_D8).toContain("Decision 8");
    expect(METHOD_S).toMatch(/\bS\b/);
  });

  it("does not stamp withhold as missing evidence or as safe", () => {
    const chrome = publishedChromeCopy().join("\n");
    for (const phrase of FORBIDDEN_JUDGE_PHRASES) {
      expect(chromeUsesForbiddenPhrase(chrome, phrase), phrase).toBe(false);
    }
    expect(chrome).toContain("This is the product, not a failure");
    expect(chrome).toContain("not treated as safe");
    expect(chrome).toContain("Geography ready is not history ready");
  });
});
