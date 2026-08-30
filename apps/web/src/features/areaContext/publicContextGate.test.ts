import { describe, expect, it } from "vitest";
import { isPublicContextEnabled } from "./publicContextGate";

describe("public context client gate", () => {
  it("defaults on for RC-v2", () => {
    expect(isPublicContextEnabled()).toBe(true);
    expect(isPublicContextEnabled("1")).toBe(true);
  });

  it("turns off for explicit falsy values", () => {
    expect(isPublicContextEnabled("0")).toBe(false);
    expect(isPublicContextEnabled("false")).toBe(false);
    expect(isPublicContextEnabled("")).toBe(false);
  });

  it("turns on for explicit truthy values", () => {
    expect(isPublicContextEnabled("true")).toBe(true);
    expect(isPublicContextEnabled("yes")).toBe(true);
    expect(isPublicContextEnabled("on")).toBe(true);
  });
});
