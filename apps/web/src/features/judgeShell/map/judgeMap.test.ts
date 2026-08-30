import { describe, expect, it } from "vitest";
import { historicalCatalog, snapshotCatalog } from "@/features/mapInteraction/fixtures";
import { rankedFillCount } from "@/features/mapInteraction";
import {
  ORDER_SHOWN_TITLE,
  ORDER_WITHHELD_TITLE,
  bindExclusiveMapLayer,
} from "./index";

describe("judgeShell/map", () => {
  it("exports MAP-B titles", () => {
    expect(ORDER_SHOWN_TITLE).toBe("Nighttime historical thermal pattern");
    expect(ORDER_WITHHELD_TITLE).toBe("Nighttime historical thermal pattern");
  });

  it("never places the B snapshot on the A rank map", () => {
    const bound = bindExclusiveMapLayer({
      lane: "A",
      historical: historicalCatalog(true),
      snapshot: snapshotCatalog(),
    });
    expect(bound?.kind).not.toBe("selected_time_snapshot");
    expect(bound?.kind).toBe("historical_ordering");
  });

  it("reports 0 fills on the withheld A catalog", () => {
    expect(rankedFillCount(historicalCatalog(false))).toBe(0);
  });
});
