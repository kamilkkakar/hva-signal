const MONTHS = [
  "Jan",
  "Feb",
  "Mar",
  "Apr",
  "May",
  "Jun",
  "Jul",
  "Aug",
  "Sep",
  "Oct",
  "Nov",
  "Dec",
] as const;

export function formatTempC(value: number): string {
  return `${value.toFixed(1)} °C`;
}

export function formatDeltaC(value: number): string {
  const sign = value > 0 ? "+" : "";
  return `${sign}${value.toFixed(2)} °C`;
}

/** Formats a bound local clock such as `2025-07-15 03:00` for first-read. */
export function formatLocalObservation(clock: string): string {
  const match = /^(\d{4})-(\d{2})-(\d{2})[ T](\d{2}:\d{2})/.exec(clock.trim());
  if (!match) {
    return clock;
  }
  const month = MONTHS[Number(match[2]) - 1];
  if (!month) {
    return clock;
  }
  return `${Number(match[3])} ${month} ${match[1]} · ${match[4]} local`;
}

export function finiteNumber(value: unknown): value is number {
  return typeof value === "number" && Number.isFinite(value);
}
