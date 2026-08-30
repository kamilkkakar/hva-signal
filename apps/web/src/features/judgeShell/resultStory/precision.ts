/** Public story precision. Full digits stay in RESCUE-I technical disclosure. */

export const PUBLIC_SEPARATION_DECIMALS = 3;
export const PUBLIC_FLOOR_DECIMALS = 2;

export function formatPublicSeparation(
  value: number | null | undefined,
): string | null {
  if (value == null || Number.isNaN(Number(value))) {
    return null;
  }
  return Number(value).toFixed(PUBLIC_SEPARATION_DECIMALS);
}

export function formatPublicFloor(
  value: number | null | undefined,
): string | null {
  if (value == null || Number.isNaN(Number(value))) {
    return null;
  }
  return Number(value).toFixed(PUBLIC_FLOOR_DECIMALS);
}
