import { describe, expect, it } from "vitest";
import {
  CROSS_CITY_HUE_FAMILIES,
  CROSS_CITY_OUTLINE_COLORS,
  citySpectrumFill,
  noneFillColorForCity,
  outlineColorForCity,
} from "./colors";
import { canopyDisplayDomain } from "./canopyDisplayScale";

describe("cross-city city-spectrum colors", () => {
  it("binds published city hue families with accessible separation", () => {
    expect(CROSS_CITY_HUE_FAMILIES.map((family) => family.id)).toEqual([
      "phoenix-az",
      "las-vegas-nv",
      "tucson-az",
      "los-angeles-ca",
      "yuma-az",
      "palm-springs-ca",
    ]);
    expect(outlineColorForCity("phoenix-az")).toMatch(/^oklch\(/);
    expect(outlineColorForCity("los-angeles-ca")).toMatch(/^oklch\(/);
    expect(CROSS_CITY_OUTLINE_COLORS["phoenix-az"]).toMatch(/^oklch\(/);
  });

  it("keeps fill inside the city hue family across metric intensity", () => {
    const domain = canopyDisplayDomain();
    const low = citySpectrumFill("phoenix-az", 0, domain, { metric: "treeCanopyPct" });
    const high = citySpectrumFill("phoenix-az", 25, domain, { metric: "treeCanopyPct" });
    expect(low).toContain("250");
    expect(high).toContain("250");
    expect(low).not.toEqual(high);
    expect(noneFillColorForCity("tucson-az")).toContain("305");
  });

  it("does not switch to a universal green palette", () => {
    const domain = { min: 0, max: 25 };
    const phoenix = citySpectrumFill("phoenix-az", 10, domain, { metric: "treeCanopyPct" });
    const vegas = citySpectrumFill("las-vegas-nv", 10, domain, { metric: "treeCanopyPct" });
    expect(phoenix).not.toEqual(vegas);
    expect(phoenix).not.toMatch(/rgb\(32, 94, 65\)/);
  });
});
