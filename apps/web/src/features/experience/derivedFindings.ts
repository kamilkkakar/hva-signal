/** Pure observation-derived findings — no hardcoded °C gap copy. */

export type TempObservation = {
  id: string;
  label: string;
  temperatureC: number;
};

export type PairwiseDelta = {
  fromId: string;
  toId: string;
  fromLabel: string;
  toLabel: string;
  deltaC: number;
};

export type DerivedThermalFindings = {
  count: number;
  highest: TempObservation | null;
  lowest: TempObservation | null;
  spanC: number | null;
  pairwise: readonly PairwiseDelta[];
  latestVsEarliestC: number | null;
};

export function deriveThermalFindings(
  observations: readonly TempObservation[],
): DerivedThermalFindings {
  const usable = observations.filter((row) => Number.isFinite(row.temperatureC));
  if (usable.length === 0) {
    return {
      count: 0,
      highest: null,
      lowest: null,
      spanC: null,
      pairwise: [],
      latestVsEarliestC: null,
    };
  }

  let highest = usable[0]!;
  let lowest = usable[0]!;
  for (const row of usable) {
    if (row.temperatureC > highest.temperatureC) highest = row;
    if (row.temperatureC < lowest.temperatureC) lowest = row;
  }

  const pairwise: PairwiseDelta[] = [];
  for (let i = 1; i < usable.length; i += 1) {
    const prev = usable[i - 1]!;
    const next = usable[i]!;
    pairwise.push({
      fromId: prev.id,
      toId: next.id,
      fromLabel: prev.label,
      toLabel: next.label,
      deltaC: next.temperatureC - prev.temperatureC,
    });
  }

  const earliest = usable[0]!;
  const latest = usable[usable.length - 1]!;

  return {
    count: usable.length,
    highest,
    lowest,
    spanC: highest.temperatureC - lowest.temperatureC,
    pairwise,
    latestVsEarliestC: latest.temperatureC - earliest.temperatureC,
  };
}

export type DerivedHistoricalFindings = {
  yearValues: readonly { year: number; meanC: number }[];
  latestVsEarliestC: number | null;
  geographyMedianChangeC: number | null;
  matchedNightCount: number | null;
};

export function deriveHistoricalFindings(input: {
  years: readonly { year: number; meanC: number }[];
  medianChangeC?: number | null;
  matchedNightCount?: number | null;
}): DerivedHistoricalFindings {
  const years = [...input.years].filter((row) => Number.isFinite(row.meanC));
  const latestVsEarliestC =
    years.length >= 2
      ? years[years.length - 1]!.meanC - years[0]!.meanC
      : null;
  return {
    yearValues: years,
    latestVsEarliestC,
    geographyMedianChangeC:
      input.medianChangeC != null && Number.isFinite(input.medianChangeC)
        ? input.medianChangeC
        : null,
    matchedNightCount:
      input.matchedNightCount != null && Number.isFinite(input.matchedNightCount)
        ? input.matchedNightCount
        : null,
  };
}
