import { describe, expect, it } from "vitest";
import { CROSS_CITY_OUTLINE_COLORS, outlineColorForCity } from "./colors";

describe("cross-city outline colors", () => {
  it("binds the published city palette", () => {
    expect(CROSS_CITY_OUTLINE_COLORS).toEqual({
      "phoenix-az": "#2F6FED",
      "los-angeles-ca": "#E67E22",
      "tucson-az": "#7B4DDB",
      "las-vegas-nv": "#0D9488",
    });
    expect(outlineColorForCity("phoenix-az")).toBe("#2F6FED");
    expect(outlineColorForCity("los-angeles-ca")).toBe("#E67E22");
  });
});
