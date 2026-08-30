import { createElement } from "react";
import { renderToStaticMarkup } from "react-dom/server";
import { describe, expect, it } from "vitest";
import { bindHistoricalPositions } from "./bind";
import { FORBIDDEN_CHART_CHROME } from "./copy";
import { clusteredResult, SELECTED_CLUSTERED_ID, separatedResult } from "./fixtures";
import { HistoricalPositionStrip } from "./HistoricalPositionStrip";
import { presentHistoricalPosition } from "./presentation";

function render(result: ReturnType<typeof clusteredResult>, selected?: string) {
  return renderToStaticMarkup(
    createElement(HistoricalPositionStrip, {
      view: presentHistoricalPosition(
        bindHistoricalPositions({ result, selectedZoneId: selected ?? null }),
      ),
    }),
  );
}

function markXs(html: string): number[] {
  return [...html.matchAll(/<circle[^>]*cx="([^"]+)"/g)]
    .map((match) => Number(match[1]))
    .filter((value) => Number.isFinite(value));
}

describe("HistoricalPositionStrip", () => {
  it("renders 25 marks and the binary comparison state, not a probability axis", () => {
    const html = render(separatedResult());
    expect(html).toContain('data-testid="historical-position-strip"');
    expect(html).toContain('data-mark-count="25"');
    expect(html).toContain("ORDERING SUPPORTED");
    expect(html).toContain("LOWER POSITION IN OWN HISTORY");
    expect(html).toContain("HIGHER POSITION IN OWN HISTORY");
    expect(html).toContain("03:00 · 2022–2024 same hour");
    expect(html).not.toContain("q_A");
    expect(html).not.toContain("probability");
    expect(html).not.toContain("%");
    for (const token of FORBIDDEN_CHART_CHROME) {
      expect(html.includes(token), token).toBe(false);
    }
  });

  it("places clustered marks together and separated marks apart", () => {
    const clusteredXs = markXs(render(clusteredResult(), SELECTED_CLUSTERED_ID));
    const separatedXs = markXs(render(separatedResult()));
    expect(clusteredXs).toHaveLength(25);
    expect(separatedXs).toHaveLength(25);
    const clusterSpan = Math.max(...clusteredXs) - Math.min(...clusteredXs);
    const separatedSpan = Math.max(...separatedXs) - Math.min(...separatedXs);
    expect(clusterSpan).toBeLessThan(4);
    expect(separatedSpan).toBeGreaterThan(80);
  });

  it("renders nothing without historical positions", () => {
    const html = renderToStaticMarkup(
      createElement(HistoricalPositionStrip, {
        view: presentHistoricalPosition(
          bindHistoricalPositions({ result: { zones: [] } }),
        ),
      }),
    );
    expect(html).toBe("");
  });
});
