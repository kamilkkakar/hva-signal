import { describe, expect, it } from "vitest";
import { isPublicContextEnabled } from "./publicContextGate";

describe("public context client gate", () => {
  it("defaults off", () => {
    expect(isPublicContextEnabled("0")).toBe(false);
    expect(isPublicContextEnabled("")).toBe(false);
    expect(isPublicContextEnabled("false")).toBe(false);
  });

  it("turns on only for explicit truthy values", () => {
    expect(isPublicContextEnabled("1")).toBe(true);
    expect(isPublicContextEnabled("true")).toBe(true);
    expect(isPublicContextEnabled("yes")).toBe(true);
    expect(isPublicContextEnabled("on")).toBe(true);
  });
});
