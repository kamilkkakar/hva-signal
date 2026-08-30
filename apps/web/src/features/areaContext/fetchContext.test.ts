import { describe, expect, it } from "vitest";
import { fetchAreaContext } from "./fetchContext";

describe("fetchAreaContext", () => {
  it("refuses a payload that authorizes a combined score", async () => {
    const fetchImpl = async () =>
      new Response(
        JSON.stringify({
          combined_score_authorized: true,
          vulnerability_score_authorized: false,
        }),
        { status: 200 },
      );
    await expect(fetchAreaContext("phoenix-demo", null, fetchImpl as typeof fetch)).rejects.toThrow(
      /combined score/,
    );
  });

  it("reads GET /areas/{area_id}/context only", async () => {
    let url = "";
    const fetchImpl = async (input: RequestInfo | URL) => {
      url = String(input);
      return new Response(
        JSON.stringify({
          combined_score_authorized: false,
          vulnerability_score_authorized: false,
          area_id: "phoenix-demo",
        }),
        { status: 200 },
      );
    };
    await fetchAreaContext("phoenix-demo", "04013107401", fetchImpl as typeof fetch);
    expect(url).toBe("/api/v1/areas/phoenix-demo/context?zone_id=04013107401");
  });
});
