import { apiUrl } from "@/api/baseUrl";
import type { AreaContextDocument } from "./types";

export async function fetchAreaContext(
  areaId: string,
  zoneId?: string | null,
  fetchImpl: typeof fetch = fetch,
): Promise<AreaContextDocument> {
  const params = zoneId
    ? `?zone_id=${encodeURIComponent(zoneId)}`
    : "";
  const response = await fetchImpl(
    apiUrl(`/api/v1/areas/${encodeURIComponent(areaId)}/context${params}`),
    { method: "GET", headers: { Accept: "application/json" } },
  );
  if (!response.ok) {
    throw new Error(`Area context could not be loaded (${response.status}).`);
  }
  const body: unknown = await response.json();
  if (!body || typeof body !== "object") {
    throw new Error("Area context response is not an object.");
  }
  const document = body as AreaContextDocument;
  if (document.combined_score_authorized !== false) {
    throw new Error("Context response must not authorize a combined score.");
  }
  if (document.vulnerability_score_authorized !== false) {
    throw new Error("Context response must not authorize a vulnerability score.");
  }
  return document;
}
