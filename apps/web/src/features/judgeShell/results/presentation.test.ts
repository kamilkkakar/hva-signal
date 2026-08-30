import { describe, expect, it } from "vitest";
import { FORBIDDEN_CARD_FACE, STAMP_ORDER_SHOWN, STAMP_ORDER_WITHHELD } from "./copy";
import { cardFaceText, cardIsDense } from "./density";
import { replay0630Snapshot, replay0701Snapshot } from "./fixtures";
import { resultCardsFromSnapshot } from "./presentation";

describe("resultCardsFromSnapshot", () => {
  it("maps 07-01 replay to ORDER WITHHELD with a dense A card", () => {
    const view = resultCardsFromSnapshot({
      snapshot: replay0701Snapshot,
      rankingState: "INSUFFICIENT_EVIDENCE",
    });
    expect(view.a.stamp).toBe(STAMP_ORDER_WITHHELD);
    expect(view.b.stamp).toBe("NOT ON THIS SURFACE");
    expect(cardIsDense(view.a)).toBe(true);
    expect(cardIsDense(view.b)).toBe(true);
    expect(view.a.values).toHaveLength(3);
    expect(view.b.values).toHaveLength(1);
    const face = `${cardFaceText(view.a)} ${cardFaceText(view.b)}`;
    for (const token of FORBIDDEN_CARD_FACE) {
      expect(face.toLowerCase()).not.toContain(token.toLowerCase());
    }
  });

  it("maps a sufficient night to ORDER SHOWN", () => {
    const view = resultCardsFromSnapshot({
      snapshot: replay0630Snapshot,
      rankingState: "READY",
    });
    expect(view.a.stamp).toBe(STAMP_ORDER_SHOWN);
    expect(cardIsDense(view.a)).toBe(true);
  });

  it("stays idle when no snapshot exists", () => {
    const view = resultCardsFromSnapshot({
      snapshot: null,
      rankingState: "INSUFFICIENT_EVIDENCE",
    });
    expect(view.a.stamp).toBe("NOT REQUESTED");
  });
});
