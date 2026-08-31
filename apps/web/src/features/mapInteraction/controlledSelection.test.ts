import { describe, expect, it, vi } from "vitest";
import {
  applyParentSelectionToMap,
  notifyParentIfUserGesture,
  resolveAuthoritativeSelection,
  shouldNotifyParentSelection,
} from "./controlledSelection";

describe("selection ownership / flicker regression", () => {
  it("does not write stale map selection back when parent advanced A→B (callback churn)", () => {
    // Reproduction: parent already chose B; map mirror still A; outbound sync
    // re-ran because onSelectedIdChange identity changed (inline lambda).
    const after = resolveAuthoritativeSelection({
      parentSelectedId: "04013107500",
      mapSelectedId: "04013107401",
      callbackIdentityChanged: true,
    });
    expect(after).toBe("04013107500");
  });

  it("keeps parent selection through rapid A→B→C→D→E advances", () => {
    const sequence = [
      "04013107401",
      "04013107500",
      "04013107601",
      "04013107602",
      "04013108802",
    ];
    let parent = sequence[0]!;
    let map = sequence[0]!;
    for (const next of sequence.slice(1)) {
      parent = next;
      parent = resolveAuthoritativeSelection({
        parentSelectedId: parent,
        mapSelectedId: map,
        callbackIdentityChanged: true,
      });
      map = parent;
    }
    expect(parent).toBe("04013108802");
    expect(map).toBe("04013108802");
  });

  it("only notifies parent on user gestures, never on mirror sync", () => {
    expect(shouldNotifyParentSelection("mirror_sync")).toBe(false);
    expect(shouldNotifyParentSelection("user_select")).toBe(true);
    expect(shouldNotifyParentSelection("user_clear")).toBe(true);

    const onChange = vi.fn();
    notifyParentIfUserGesture("mirror_sync", "04013107500", onChange);
    expect(onChange).not.toHaveBeenCalled();
    notifyParentIfUserGesture("user_select", "04013107500", onChange);
    expect(onChange).toHaveBeenCalledWith("04013107500");
  });

  it("mirrors parent into map via set_selected without toggling", () => {
    expect(applyParentSelectionToMap("04013107500")).toEqual({
      type: "set_selected",
      geoid: "04013107500",
    });
    expect(applyParentSelectionToMap(null)).toEqual({
      type: "set_selected",
      geoid: null,
    });
  });
});
