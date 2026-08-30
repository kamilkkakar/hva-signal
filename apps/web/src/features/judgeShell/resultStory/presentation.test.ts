import { describe, expect, it } from "vitest";
import {
  INSUFFICIENT_HEADLINE,
  STAMP_AWAITING,
  STAMP_SUPPORTED,
  STAMP_WITHHELD,
  SUFFICIENT_HEADLINE,
} from "./copy";
import {
  ORACLE_S_INSUFFICIENT_PUBLIC,
  ORACLE_S_SUFFICIENT_PUBLIC,
  oracle0630Snapshot,
  oracle0701Snapshot,
} from "./fixtures";
import { presentResultStory } from "./presentation";

describe("presentResultStory", () => {
  it("maps 2022-06-30 sufficient 25 fills to the compare story", () => {
    const view = presentResultStory({ snapshot: oracle0630Snapshot });
    expect(view.kind).toBe("sufficient");
    expect(view.stamp).toBe(STAMP_SUPPORTED);
    expect(view.headline).toBe(SUFFICIENT_HEADLINE);
    expect(view.how.observedSeparation).toBe(ORACLE_S_SUFFICIENT_PUBLIC);
    expect(view.how.minimumSeparation).toBe("0.10");
    expect(view.how.spatialDifferentiation).toContain("Supported");
    expect(view.context.map((item) => item.value)).toEqual([
      "25 zones",
      "03:00 local",
      "Historical comparison 2022–2024",
    ]);
  });

  it("maps 2022-07-01 insufficient 0 fills to the unranked story", () => {
    const view = presentResultStory({ snapshot: oracle0701Snapshot });
    expect(view.kind).toBe("insufficient");
    expect(view.stamp).toBe(STAMP_WITHHELD);
    expect(view.headline).toBe(INSUFFICIENT_HEADLINE);
    expect(view.summary).toContain("Zones stay unranked");
    expect(view.how.observedSeparation).toBe(ORACLE_S_INSUFFICIENT_PUBLIC);
    expect(view.how.spatialDifferentiation).toContain("Withheld");
  });

  it("awaits before a completed analysis", () => {
    const view = presentResultStory({ snapshot: null });
    expect(view.kind).toBe("awaiting");
    expect(view.stamp).toBe(STAMP_AWAITING);
    expect(view.how.observedSeparation).toBeNull();
  });
});
