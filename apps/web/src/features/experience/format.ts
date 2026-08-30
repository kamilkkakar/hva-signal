export function formatTempC(value: number): string {
  return `${value.toFixed(1)} °C`;
}

export function formatDeltaC(value: number): string {
  const sign = value > 0 ? "+" : "";
  return `${sign}${value.toFixed(2)} °C`;
}

export function finiteNumber(value: unknown): value is number {
  return typeof value === "number" && Number.isFinite(value);
}
