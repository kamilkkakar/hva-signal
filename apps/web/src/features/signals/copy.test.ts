import { describe, expect, it } from "vitest";
import {
  FORBIDDEN_AUTH_PHRASES,
  FORBIDDEN_COMBINED_PHRASES,
  FORBIDDEN_L6_PHRASES,
  FORBIDDEN_LIVE_CHROME,
  FORBIDDEN_SPEND_PHRASES,
  REFERENCE_NOT_PREPARED_ACQUISITION_COPY,
  REFERENCE_NOT_PREPARED_COPY,
  REFERENCE_NOT_PREPARED_LOCK_COPY,
  REFERENCE_NOT_PREPARED_STAMP,
  REUSE_ONLY_COPY,
  publishedSignalCopy,
} from "./copy";

describe("signal copy lock", () => {
  it("keeps NOT_PREPARED from reading as low risk", () => {
    const blob = [
      REFERENCE_NOT_PREPARED_STAMP,
      REFERENCE_NOT_PREPARED_COPY,
      REFERENCE_NOT_PREPARED_ACQUISITION_COPY,
      REFERENCE_NOT_PREPARED_LOCK_COPY,
    ]
      .join("\n")
      .toLowerCase();
    expect(REFERENCE_NOT_PREPARED_STAMP).toBe("REFERENCE NOT PREPARED");
    expect(blob).toContain("not treated as safe");
    expect(blob).toContain("not prepared");
    for (const phrase of FORBIDDEN_L6_PHRASES) {
      expect(blob.includes(phrase)).toBe(false);
    }
    expect(blob).not.toContain("preparedness priority");
    expect(blob).not.toMatch(/\bs\s*[:=]\s*0\b/);
  });

  it("states reuse-only and never publishes spend or live chrome", () => {
    const blob = publishedSignalCopy().join("\n").toLowerCase();
    expect(REUSE_ONLY_COPY.toLowerCase()).toContain("reuse-only");
    expect(blob).toContain("does not request live acquisition");
    for (const phrase of FORBIDDEN_SPEND_PHRASES) {
      expect(blob.includes(phrase)).toBe(false);
    }
    for (const phrase of FORBIDDEN_LIVE_CHROME) {
      expect(blob.includes(phrase)).toBe(false);
    }
  });

  it("never authorizes a combined score or an account wall", () => {
    const blob = publishedSignalCopy().join("\n").toLowerCase();
    expect(blob).toContain("combined score is not authorized");
    for (const phrase of FORBIDDEN_COMBINED_PHRASES) {
      expect(blob.includes(phrase)).toBe(false);
    }
    for (const phrase of FORBIDDEN_AUTH_PHRASES) {
      expect(blob.includes(phrase)).toBe(false);
    }
  });
});
