import { apiUrl } from "@/api/baseUrl";
import type { MatchedNighttimeView, ObservedSequenceView } from "./types";

export async function fetchMatchedNighttimeWindow(
  geoid: string,
  fetchImpl: typeof fetch = fetch,
): Promise<MatchedNighttimeView> {
  const response = await fetchImpl(
    apiUrl(`/api/v1/demo/matched-nighttime-window?area_id=phoenix-demo&geoid=${encodeURIComponent(geoid)}`),
    { method: "GET", headers: { Accept: "application/json" } },
  );
  if (!response.ok) {
    throw new Error(`Matched nighttime window could not be loaded (${response.status}).`);
  }
  const body: unknown = await response.json();
  if (!body || typeof body !== "object") {
    throw new Error("Matched nighttime window response is not an object.");
  }
  return body as MatchedNighttimeView;
}

export async function fetchObservedThermalInstants(
  geoid: string,
  fetchImpl: typeof fetch = fetch,
): Promise<ObservedSequenceView> {
  const response = await fetchImpl(
    apiUrl(`/api/v1/demo/observed-thermal-instants?area_id=phoenix-demo&geoid=${encodeURIComponent(geoid)}`),
    { method: "GET", headers: { Accept: "application/json" } },
  );
  if (!response.ok) {
    throw new Error(`Observed thermal instants could not be loaded (${response.status}).`);
  }
  const body: unknown = await response.json();
  if (!body || typeof body !== "object") {
    throw new Error("Observed thermal instants response is not an object.");
  }
  return body as ObservedSequenceView;
}
