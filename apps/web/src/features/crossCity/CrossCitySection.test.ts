import { createElement } from "react";
import { renderToStaticMarkup } from "react-dom/server";
import { describe, expect, it } from "vitest";
import { CROSS_CITY_SECTION_COPY, CrossCitySection } from "./CrossCitySection";

describe("cross-city section copy", () => {
  it("keeps the section descriptive and non-causal", () => {
    const blob = Object.values(CROSS_CITY_SECTION_COPY).join(" ").toLowerCase();
    expect(blob).not.toContain("causes");
    expect(blob).not.toContain("drives heat");
    expect(blob).not.toContain("proves need");
    expect(blob).not.toContain("best city");
  });

  it("mounts with the comparison clock and Phoenix area-analysis path by default", () => {
    const html = renderToStaticMarkup(createElement(CrossCitySection));
    expect(html).toContain("2024-07-08 15:00");
    expect(html).toContain('href="#happening"');
    expect(html).toContain("Open area analysis");
    expect(html).toContain('data-testid="cross-city-loading"');
  });
});
