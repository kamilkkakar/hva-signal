import { describe, expect, it } from "vitest";
import { CONTEXT_REFERENCE_COPY } from "./ZonePanel";

describe("zone context reference copy", () => {
  it("keeps structural context separate from the thermal observation timestamp", () => {
    expect(CONTEXT_REFERENCE_COPY).toContain("tree canopy 2021");
    expect(CONTEXT_REFERENCE_COPY).toContain("ACS 2020–2024 5-year estimates");
    expect(CONTEXT_REFERENCE_COPY).toContain(
      "not measurements from the thermal observation timestamp",
    );
  });
});
