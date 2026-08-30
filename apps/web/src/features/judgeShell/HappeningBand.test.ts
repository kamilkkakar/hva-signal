import { createElement } from "react";
import { renderToStaticMarkup } from "react-dom/server";
import { describe, expect, it } from "vitest";
import { THERMAL_SPATIAL_DIFFERENTIATION_INSUFFICIENT } from "@/utils/mapLayer";
import { HappeningBand } from "./HappeningBand";
import { happeningView } from "./happening";

function markup(
  happening: ReturnType<typeof happeningView>,
): string {
  return renderToStaticMarkup(
    createElement(HappeningBand, {
      happening,
      busy: false,
      showRecovery: false,
      canResubmit: false,
      onResubmit: () => undefined,
    }),
  );
}

function evidenceStateText(html: string): string {
  const match = html.match(
    /data-testid="evidence-state"[^>]*>([^<]*)</,
  );
  return match?.[1] ?? "";
}

function visibleText(html: string): string {
  return html.replace(/<[^>]+>/g, " ").replace(/\s+/g, " ");
}

describe("HappeningBand assistive stamp", () => {
  it("announces SPATIAL ORDERING WITHHELD after a flat night, not the ranking enum", () => {
    const html = markup(
      happeningView({
        status: "complete",
        busy: false,
        stalled: false,
        rankingState: "INSUFFICIENT_EVIDENCE",
        limitations: [THERMAL_SPATIAL_DIFFERENTIATION_INSUFFICIENT],
      }),
    );
    expect(html).toContain('data-testid="happening-stamp"');
    expect(html).toContain('data-ranking-state="INSUFFICIENT_EVIDENCE"');
    expect(evidenceStateText(html)).toBe("SPATIAL ORDERING WITHHELD");
    expect(visibleText(html)).toContain("SPATIAL ORDERING WITHHELD");
    expect(visibleText(html)).not.toContain("ORDER WITHHELD");
    expect(visibleText(html)).not.toContain("INSUFFICIENT_EVIDENCE");
    expect(visibleText(html)).not.toContain("INSUFFICIENT EVIDENCE");
  });

  it("announces SPATIAL ORDERING SUPPORTED when ranking is ready", () => {
    const html = markup(
      happeningView({
        status: "complete",
        busy: false,
        stalled: false,
        rankingState: "READY",
        limitations: [],
      }),
    );
    expect(evidenceStateText(html)).toBe("SPATIAL ORDERING SUPPORTED");
    expect(visibleText(html)).not.toContain("ORDER SHOWN");
    expect(visibleText(html)).not.toContain("READY");
  });

  it("announces NOT REQUESTED on first paint, not INSUFFICIENT_EVIDENCE", () => {
    const html = markup(
      happeningView({
        status: null,
        busy: false,
        stalled: false,
        rankingState: "INSUFFICIENT_EVIDENCE",
        limitations: [],
      }),
    );
    expect(evidenceStateText(html)).toBe("NOT REQUESTED");
    expect(visibleText(html)).not.toContain("INSUFFICIENT_EVIDENCE");
  });
});
