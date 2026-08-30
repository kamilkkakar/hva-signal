import { readFileSync } from "node:fs";
import path from "node:path";
import { fileURLToPath } from "node:url";
import { describe, expect, it } from "vitest";
import {
  chromeLeaksMethod,
  presentSignalA,
  signalAHoverLine,
} from "./presentation";
import { STAMP_HISTORY_NOT_PREPARED, STAMP_ORDER_SHOWN, STAMP_ORDER_WITHHELD } from "./copy";

const here = path.dirname(fileURLToPath(import.meta.url));

describe("presentSignalA", () => {
  it("shows an order without Method nouns on chrome", () => {
    const view = presentSignalA({
      kind: "order_shown",
      zoneId: "04013107800",
      order: 1,
    });
    expect(view.stamp).toBe(STAMP_ORDER_SHOWN);
    expect(view.rankedFillCount).toBe(25);
    expect(view.outlineCount).toBe(25);
    expect(view.hoverEnabled).toBe(true);
    expect(view.hoverLine).toContain("Nighttime order 1 of 25");
    expect(view.doesNotBlockSignalB).toBe(true);
    expect(chromeLeaksMethod(view)).toBe(false);
  });

  it("treats insufficient spatial order as a feature, not a failure stamp", () => {
    const view = presentSignalA({ differentiationState: "INSUFFICIENT" });
    expect(view.kind).toBe("order_withheld");
    expect(view.stamp).toBe(STAMP_ORDER_WITHHELD);
    expect(view.stamp).not.toBe("INSUFFICIENT EVIDENCE");
    expect(view.insufficientIsFeature).toBe(true);
    expect(view.featureLine).toContain("flat night");
    expect(view.rankedFillCount).toBe(0);
    expect(view.outlineCount).toBe(25);
    expect(view.hoverEnabled).toBe(false);
    expect(chromeLeaksMethod(view)).toBe(false);
  });

  it("keeps history-not-prepared off the withhold stamp", () => {
    const history = presentSignalA({ historyPrepared: false });
    const withheld = presentSignalA({ differentiationState: "INSUFFICIENT" });
    expect(history.stamp).toBe(STAMP_HISTORY_NOT_PREPARED);
    expect(history.kind).toBe("history_not_prepared");
    expect(history.stamp).not.toBe(withheld.stamp);
    expect(history.body).toContain("Geography ready is not history ready");
    expect(history.outlineCount).toBe(25);
    expect(history.rankedFillCount).toBe(0);
    expect(chromeLeaksMethod(history)).toBe(false);
  });

  it("maps thin history separately from a flat night", () => {
    const thin = presentSignalA({
      limitations: ["INSUFFICIENT_REFERENCE"],
    });
    expect(thin.kind).toBe("history_too_thin");
    expect(thin.stamp).toBe("HISTORY TOO THIN");
    expect(thin.stamp).not.toBe(STAMP_ORDER_WITHHELD);
  });

  it("withholds hover unless an order is shown", () => {
    expect(
      signalAHoverLine({
        kind: "order_withheld",
        zoneId: "x",
        order: 3,
      }),
    ).toBeNull();
    expect(
      signalAHoverLine({
        kind: "history_not_prepared",
        zoneId: "x",
        order: 3,
      }),
    ).toBeNull();
    expect(
      signalAHoverLine({
        kind: "order_shown",
        zoneId: "x",
        order: 3,
      }),
    ).toBe("Zone x · Nighttime order 3 of 25 · Versus this zone's own 3 a.m. nights");
  });

  it("does not change q_A or Decision 8 math", () => {
    const presentation = readFileSync(path.join(here, "presentation.ts"), "utf8");
    const bind = readFileSync(path.join(here, "fromResult.ts"), "utf8");
    for (const src of [presentation, bind]) {
      expect(src).not.toMatch(/observed_spread\s*[<>=]/);
      expect(src).not.toContain("0.10");
      expect(src).not.toContain("midrank");
      expect(src).not.toContain("ECDF");
      expect(src).not.toMatch(/zone\.q_A/);
    }
  });
});
