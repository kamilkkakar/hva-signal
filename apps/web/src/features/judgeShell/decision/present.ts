import { MISSING_FIELD, SELECT_AREA } from "./copy";
import type {
  MatchedNighttimeView,
  ObservedSequenceView,
  PresentedMatched,
  PresentedSequence,
  SectionStatus,
} from "./types";

const YEAR_KEYS = ["2022", "2023", "2024"] as const;
const INSTANT_ORDER = ["03:00_D", "15:00", "21:00", "03:00_D+1"] as const;

function finite(value: unknown): value is number {
  return typeof value === "number" && Number.isFinite(value);
}

export function presentMatched(
  geoid: string | null,
  doc: MatchedNighttimeView | null,
  error: string | null,
): PresentedMatched {
  if (!geoid) {
    return emptyMatched("UNKNOWN", SELECT_AREA);
  }
  if (error || !doc) {
    return emptyMatched("INSUFFICIENT", error ?? MISSING_FIELD);
  }
  const years = YEAR_KEYS.flatMap((year) => {
    const meanC = doc.selected_area?.mean_by_year?.[year];
    return finite(meanC) ? [{ year, meanC }] : [];
  });
  if (years.length !== 3) {
    return emptyMatched("INSUFFICIENT", MISSING_FIELD);
  }
  const change = doc.selected_area?.change_2024_vs_2022;
  const median = doc.analysis_geography?.median_change_2024_vs_2022;
  const nightsWarmer = doc.selected_area?.matched_nights_warmer;
  const nightsTotal = doc.selected_area?.matched_nights;
  if (!finite(change) || !finite(median) || !finite(nightsWarmer) || !finite(nightsTotal)) {
    return emptyMatched("INSUFFICIENT", MISSING_FIELD);
  }
  return {
    status: "AVAILABLE",
    reason: null,
    years,
    change2024vs2022: change,
    medianChange: median,
    nightsWarmer,
    nightsTotal,
  };
}

export function presentObserved(
  geoid: string | null,
  doc: ObservedSequenceView | null,
  error: string | null,
): PresentedSequence {
  if (!geoid) {
    return emptySequence("UNKNOWN", SELECT_AREA);
  }
  if (error || !doc) {
    return emptySequence("INSUFFICIENT", error ?? MISSING_FIELD);
  }
  const byId = new Map((doc.observations ?? []).map((row) => [row.instant_id, row]));
  const instants = [];
  for (const instantId of INSTANT_ORDER) {
    const row = byId.get(instantId);
    if (!row || !finite(row.temperature_c) || !row.date || !row.local_time) {
      return emptySequence("INSUFFICIENT", MISSING_FIELD);
    }
    if ((instantId === "15:00" || instantId === "21:00") && "q_A" in row) {
      return emptySequence("INSUFFICIENT", MISSING_FIELD);
    }
    instants.push({
      instantId,
      label: row.label ?? instantId,
      date: row.date,
      localTime: row.local_time,
      temperatureC: row.temperature_c,
      activityId: row.activity_id ?? null,
    });
  }
  const differences = (doc.direct_differences ?? []).flatMap((row) => {
    if (!row.from_instant_id || !row.to_instant_id || !finite(row.delta_c)) {
      return [];
    }
    return [{ fromId: row.from_instant_id, toId: row.to_instant_id, deltaC: row.delta_c }];
  });
  if (differences.length !== 3) {
    return emptySequence("INSUFFICIENT", MISSING_FIELD);
  }
  return { status: "AVAILABLE", reason: null, instants, differences };
}

function emptyMatched(status: SectionStatus, reason: string): PresentedMatched {
  return {
    status,
    reason,
    years: [],
    change2024vs2022: null,
    medianChange: null,
    nightsWarmer: null,
    nightsTotal: null,
  };
}

function emptySequence(status: SectionStatus, reason: string): PresentedSequence {
  return { status, reason, instants: [], differences: [] };
}

export function formatDeltaC(value: number): string {
  const sign = value > 0 ? "+" : "";
  return `${sign}${value.toFixed(2)} C`;
}

export function formatTempC(value: number): string {
  return `${value.toFixed(1)} C`;
}
