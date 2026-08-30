/** Public Signal B map stays off until a stitch that cannot reuse the A rank machine. */
export const SIGNAL_B_NEUTRAL_MAP_ENABLED = false;

export function signalBMapIsEnabled(override?: boolean): boolean {
  if (typeof override === "boolean") {
    return override;
  }
  return SIGNAL_B_NEUTRAL_MAP_ENABLED;
}
