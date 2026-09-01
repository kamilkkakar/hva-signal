import { createElement } from "react";
import { renderToStaticMarkup } from "react-dom/server";
import { describe, expect, it } from "vitest";
import { MapInteractionChrome } from "./MapInteractionChrome";
import { historicalCatalog, snapshotCatalog } from "./fixtures";
import { presentMapInteraction } from "./present";
import { initialInteractionState, reduceInteraction } from "./state";

function firstRead(html: string): string {
  return html.replace(/<details\b[^>]*>[\s\S]*?<\/details>/gi, "");
}

describe("map interaction first-read chrome", () => {
  it("demotes GEOID identifiers behind closed details", () => {
    const catalog = historicalCatalog(true);
    const geoid = catalog.zones[0]?.geoid ?? "";
    const view = presentMapInteraction({
      enabled: true,
      catalog,
      state: initialInteractionState(),
    });
    const html = renderToStaticMarkup(
      createElement(MapInteractionChrome, {
        view,
        dispatch: () => undefined,
      }),
    );
    expect(html).toContain("<details");
    expect(html).toContain('data-testid="map-advanced-chrome"');
    expect(html).toContain("Zone identifiers (advanced)");
    expect(html).toContain('data-testid="map-interaction-list-wrap"');
    expect(html).not.toMatch(/<details[^>]*\sopen[\s>]/);
    const visible = firstRead(html);
    expect(visible).not.toContain(geoid);
    expect(visible).not.toMatch(/\bGEOID\b/);
    expect(visible).not.toContain("phoenix-demo");
    expect(visible).not.toContain("INTERVENTION PRIORITY");
    expect(visible).not.toMatch(/backend order/i);
  });

  it("does not use a raw GEOID as the selected-zone heading", () => {
    const catalog = historicalCatalog(true);
    const geoid = catalog.zones[0]?.geoid ?? "";
    let state = initialInteractionState();
    state = reduceInteraction(state, { type: "select", geoid }, catalog);
    const view = presentMapInteraction({ enabled: true, catalog, state });
    const html = renderToStaticMarkup(
      createElement(MapInteractionChrome, {
        view,
        dispatch: () => undefined,
      }),
    );
    expect(html).toContain("Selected analysis zone");
    const heading = html.match(
      /data-testid="detail-zone-heading"[^>]*>([^<]*)</,
    );
    expect(heading?.[1]).toBe("Selected analysis zone");
    expect(heading?.[1]).not.toContain(geoid);
  });

  it("shows selected-time temperature and the actual observation clock instead of historical position copy", () => {
    const catalog = snapshotCatalog(false);
    const geoid = catalog.zones[0]?.geoid ?? "";
    let state = initialInteractionState();
    state = reduceInteraction(state, { type: "select", geoid }, catalog);
    const view = presentMapInteraction({ enabled: true, catalog, state });
    const html = renderToStaticMarkup(
      createElement(MapInteractionChrome, {
        view,
        dispatch: () => undefined,
        catalogKind: catalog.kind,
        fillKind: catalog.fill_kind,
      }),
    );

    expect(html).toContain('data-testid="detail-selected-time-value"');
    expect(html).toContain("39.9 °C");
    expect(html).toContain("15 Jul 2024 · 15:00 local");
    expect(html).not.toContain("Position within this zone&#x27;s own 03:00 historical reference");
  });
});
