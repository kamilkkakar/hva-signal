import { PLACE_INDEX } from "../../mocks/placeSearchFixtures";
import { PHOENIX_DEMO_AREA_ID, type CensusPlace, type PlaceSearchOutcome } from "./types";

const USPS = /^[A-Z]{2}$/;

export type ParsedPlaceQuery = {
  raw: string;
  name: string;
  state: string | null;
  geoid: string | null;
};

export function parsePlaceQuery(raw: string): ParsedPlaceQuery {
  const trimmed = raw.trim();
  if (/^\d{7}$/.test(trimmed)) {
    return { raw: trimmed, name: "", state: null, geoid: trimmed };
  }
  const comma = trimmed.match(/^(.*?)[, ]+([A-Za-z]{2})$/);
  const namePart = comma?.[1];
  const statePart = comma?.[2];
  if (namePart && statePart) {
    return {
      raw: trimmed,
      name: normalizeName(namePart),
      state: statePart.toUpperCase(),
      geoid: null,
    };
  }
  return { raw: trimmed, name: normalizeName(trimmed), state: null, geoid: null };
}

export function normalizeName(value: string): string {
  return value
    .toLowerCase()
    .replace(/\b(city|village|cdp|municipality|town)\b/g, "")
    .replace(/[^a-z0-9]+/g, " ")
    .trim();
}

export function searchCensusPlaces(query: string): PlaceSearchOutcome {
  const trimmed = query.trim();
  if (!trimmed) {
    return { kind: "idle" };
  }

  const parsed = parsePlaceQuery(trimmed);
  if (normalizeName(trimmed) === PHOENIX_DEMO_AREA_ID.replace("-", " ")) {
    return { kind: "unknown", query: trimmed };
  }

  if (parsed.geoid) {
    const match = PLACE_INDEX.find((row) => row.place_geoid === parsed.geoid);
    return match
      ? { kind: "unique", query: trimmed, place: match }
      : { kind: "unknown", query: trimmed };
  }

  if (parsed.state && !USPS.test(parsed.state)) {
    return { kind: "unknown", query: trimmed };
  }

  const candidates = PLACE_INDEX.filter((row) => {
    if (parsed.state && row.state_abbreviation !== parsed.state) {
      return false;
    }
    const short = normalizeName(row.place_name);
    const official = normalizeName(row.official_name);
    return short === parsed.name || official === parsed.name;
  });

  const only = candidates[0];
  if (candidates.length === 0 || !only) {
    return { kind: "unknown", query: trimmed };
  }
  if (candidates.length === 1) {
    return { kind: "unique", query: trimmed, place: only };
  }
  return { kind: "ambiguous", query: trimmed, candidates };
}

export function candidatesForOutcome(outcome: PlaceSearchOutcome): CensusPlace[] {
  if (outcome.kind === "unique") {
    return [outcome.place];
  }
  if (outcome.kind === "ambiguous" || outcome.kind === "querying") {
    return outcome.candidates;
  }
  return [];
}

export function phoenixDemoIsSearchable(): boolean {
  return PLACE_INDEX.some(
    (row) =>
      row.place_geoid === PHOENIX_DEMO_AREA_ID ||
      normalizeName(row.place_name) === "phoenix demo",
  );
}
