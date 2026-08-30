/** Neutral cached Signal B map. One shared ink. No AOI stretch. */
export const SIGNAL_B_NEUTRAL_MAP_ENABLED = true;

export function signalBMapIsEnabled(override?: boolean): boolean {
  if (typeof override === "boolean") {
    return override;
  }
  return SIGNAL_B_NEUTRAL_MAP_ENABLED;
}
