import { describe, expect, it } from "vitest";
import { isLongToken, TOKEN_LIMIT, truncateToken } from "./copyableToken";

const GEOMETRY =
  "US_CENSUS_TIGERLINE.CENSUS_TRACT.2025.AZ.PHX_DEMO_AOI_POLICY_V1.3f16870f";
const POLICY =
  "PHX_NORMALIZED_HAZARD_SPREAD_V1_TOP3_BOTTOM3_QA_FLOOR_0P10";

describe("truncateToken", () => {
  it("leaves short identifiers intact", () => {
    expect(truncateToken("PHX_ZTSI_REF_V1")).toBe("PHX_ZTSI_REF_V1");
    expect(isLongToken("PHX_ZTSI_REF_V1")).toBe(false);
  });

  it("shortens census geometry and Decision 8 policy tokens", () => {
    expect(isLongToken(GEOMETRY)).toBe(true);
    expect(isLongToken(POLICY)).toBe(true);
    expect(truncateToken(GEOMETRY).length).toBeLessThan(GEOMETRY.length);
    expect(truncateToken(GEOMETRY)).toContain("…");
    expect(truncateToken(GEOMETRY)).toMatch(/^US_CENSUS_TI…/);
    expect(truncateToken(GEOMETRY)).toMatch(/3f16870f$/);
    expect(truncateToken(POLICY)).toMatch(/FLOOR_0P10$/);
  });

  it("does not invent a shorter form at the exact limit", () => {
    const exact = "x".repeat(TOKEN_LIMIT);
    expect(truncateToken(exact)).toBe(exact);
    expect(isLongToken(exact)).toBe(false);
  });
});
