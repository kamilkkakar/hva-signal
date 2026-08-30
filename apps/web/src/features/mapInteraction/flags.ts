/** Interaction chrome stays off until stitch mounts it. Production MapStage is unchanged. */
export const MAP_INTERACTION_ENABLED = false;

export function mapInteractionIsEnabled(override?: boolean): boolean {
  if (typeof override === "boolean") {
    return override;
  }
  return MAP_INTERACTION_ENABLED;
}
