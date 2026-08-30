import { createElement } from "react";
import { renderToStaticMarkup } from "react-dom/server";
import { describe, expect, it } from "vitest";
import { bindHistoricalPositions } from "./bind";
import { clusteredResult, SELECTED_CLUSTERED_ID } from "./fixtures";
import { presentHistoricalPosition } from "./presentation";
import { SelectedZonePosition } from "./SelectedZonePosition";

function render(selectedZoneId: string | null) {
  return renderToStaticMarkup(
    createElement(SelectedZonePosition, {
      view: presentHistoricalPosition(
        bindHistoricalPositions({
          result: clusteredResult(),
          selectedZoneId,
        }),
      ),
      selectedZoneId,
    }),
  );
}

describe("SelectedZonePosition", () => {
  it("keeps the empty selected-zone poster until a zone is chosen", () => {
    const html = render(null);
    expect(html).toContain("Click a zone. No zone selected.");
    expect(html).not.toContain("q_A");
  });

  it("puts a single marker on the own-history axis and keeps exact q_A in details", () => {
    const html = render(SELECTED_CLUSTERED_ID);
    expect(html).toContain('data-testid="selected-zone-position"');
    expect(html).toContain(`Zone ${SELECTED_CLUSTERED_ID}`);
    expect(html).toContain("This zone’s historical position");
    expect(html).toContain("LOWER POSITION IN OWN HISTORY");
    const detailsStart = html.indexOf('data-testid="selected-zone-qa-details"');
    expect(detailsStart).toBeGreaterThan(-1);
    const chrome = html.slice(0, detailsStart);
    expect(chrome).not.toContain("q_A");
    expect(html.slice(detailsStart)).toContain("q_A 0.200");
  });
});
