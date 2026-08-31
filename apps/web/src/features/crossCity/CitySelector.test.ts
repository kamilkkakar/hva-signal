import { createElement } from "react";
import { renderToStaticMarkup } from "react-dom/server";
import { describe, expect, it } from "vitest";
import { CitySelector } from "./CitySelector";

describe("cross-city selector", () => {
  it("renders the fixed allowlist and no live search input", () => {
    const html = renderToStaticMarkup(
      createElement(CitySelector, {
        selectedCityId: "phoenix-az",
        onSelect: () => undefined,
      }),
    );

    expect(html).toContain("Phoenix, AZ");
    expect(html).toContain("Las Vegas, NV");
    expect(html).toContain("Tucson, AZ");
    expect(html).toContain("Los Angeles, CA");
    expect(html).toContain("<select");
    expect(html).not.toContain('type="search"');
    expect(html).not.toContain("places?q=");
  });
});
