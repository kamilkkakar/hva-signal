import { readFileSync } from "node:fs";
import { describe, expect, it } from "vitest";
import { acceptLiveObservation, liveObservationLabel, type LiveObservationResponse } from "./liveObservation";

const captured = JSON.parse(readFileSync(new URL(
  "../../../../api/tests/fixtures/live/phoenix_2021_empty_response.json", import.meta.url,
), "utf8")) as LiveObservationResponse;
const request = {
  cityId: "phoenix-az" as const,
  requestedLocal: "2021-08-14T15:00:00",
  zoneIds: captured.analysis!.zones!.map((row) => row.zone_id),
};
function populated(): LiveObservationResponse {
  const body = structuredClone(captured);
  body.analysis!.zones!.forEach((row) => {
    row.temperature_c = 38.5; row.tile_count = 1; row.coverage_status = "valid";
  });
  body.analysis!.bindable_temperature_values = 25;
  body.analysis!.source_tile_count = 25;
  return body;
}

describe("live observation identity", () => {
  it("rejects the actual empty 2021 response instead of repeating its cache-success wording", () => {
    expect(() => acceptLiveObservation(captured, request)).toThrow("No usable zone temperatures");
  });

  it("keeps the completed timestamp and source attached to the accepted result", () => {
    const accepted = acceptLiveObservation(populated(), request);
    expect(liveObservationLabel(accepted)).toContain("14 Aug 2021 · 15:00 local");
    expect(liveObservationLabel(accepted)).toContain("Cached live result");
    expect(accepted.source).toBe("fortyguard_cached");
    expect(accepted.partial).toBe(false);
  });

  it.each([
    ["city", "Tucson"], ["local_datetime", "2024-07-08T15:00:00"],
    ["timezone", "UTC"], ["aggregation_contract", "daily_aggregate"],
  ])("rejects mismatched %s", (key, value) => {
    const body = populated();
    Object.assign(body.analysis!, { [key]: value });
    expect(() => acceptLiveObservation(body, request)).toThrow("does not match");
  });

  it.each(["foreign", "duplicate", "missing"])("rejects %s zone geometry", (mode) => {
    const body = populated();
    const rows = body.analysis!.zones!;
    if (mode === "foreign") rows[0]!.zone_id = "99999999999";
    if (mode === "duplicate") rows[0]!.zone_id = rows[1]!.zone_id;
    if (mode === "missing") rows.pop();
    expect(() => acceptLiveObservation(body, request)).toThrow("geography");
  });

  it.each([NaN, Infinity, "38.5", true])("rejects invalid temperature %s", (value) => {
    const body = populated();
    Object.assign(body.analysis!.zones![0]!, { temperature_c: value });
    expect(() => acceptLiveObservation(body, request)).toThrow("invalid zone temperatures");
  });

  it("rejects incorrect source tile totals", () => {
    const body = populated();
    body.analysis!.source_tile_count = 0;
    expect(() => acceptLiveObservation(body, request)).toThrow("inconsistent temperature coverage");
  });

  it("shows real partial coverage while retaining nulls", () => {
    const body = populated();
    body.status = "partial_observation";
    body.acquisition_status = "cache_hit";
    body.analysis!.zones![0] = { ...body.analysis!.zones![0]!, temperature_c: null, tile_count: 0, coverage_status: "missing" };
    body.analysis!.bindable_temperature_values = 24;
    body.analysis!.source_tile_count = 24;
    const accepted = acceptLiveObservation(body, request);
    expect(accepted.partial).toBe(true);
    expect(accepted.analysis.zones[0]!.temperature_c).toBeNull();
    expect(liveObservationLabel(accepted)).toContain("Partial zone coverage");
    expect(liveObservationLabel(accepted)).toContain("Cached live result");
  });
});
