import { describe, expect, it } from "vitest";
import { placeSearchRouteFromHash } from "./hashRoute";

describe("place search hash route", () => {
  it("treats #/phoenix-demo as the legacy replay, not national Phoenix", () => {
    expect(placeSearchRouteFromHash("#/phoenix-demo")).toBe("phoenix-demo");
    expect(placeSearchRouteFromHash("#/phoenix-demo/replay")).toBe("phoenix-demo");
    expect(placeSearchRouteFromHash("#/")).toBe("national");
    expect(placeSearchRouteFromHash("#/0455000")).toBe("national");
  });
});
