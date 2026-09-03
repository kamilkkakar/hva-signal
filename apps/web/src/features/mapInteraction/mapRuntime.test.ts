import { describe, expect, it, vi } from "vitest";
import { startMapRuntime } from "./mapRuntime";

describe("startMapRuntime", () => {
  it("returns the normal renderer unchanged", () => {
    const renderer = { id: "map" };

    expect(startMapRuntime(() => renderer)).toEqual({ state: "ready", map: renderer });
  });

  it("converts a WebGL construction failure into an unavailable state", () => {
    const create = vi.fn(() => {
      throw new Error("Failed to initialize WebGL");
    });

    expect(startMapRuntime(create)).toEqual({ state: "unavailable", map: null });
    expect(create).toHaveBeenCalledOnce();
  });
});
