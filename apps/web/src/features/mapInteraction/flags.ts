/** I-MAP stitch defaults on. Production MapStage remains a separate host. */
export const MAP_INTERACTION_ENABLED = true;

export function mapInteractionIsEnabled(override?: boolean): boolean {
  if (typeof override === "boolean") {
    return override;
  }
  return MAP_INTERACTION_ENABLED;
}
