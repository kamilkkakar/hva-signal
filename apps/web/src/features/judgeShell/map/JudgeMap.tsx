import {
  MapInteractionStage,
  bindExclusiveMapLayer,
  type InteractionCatalog,
} from "@/features/mapInteraction";

export type JudgeMapProps = {
  lane: "A" | "B";
  historical: InteractionCatalog | null;
  snapshot?: InteractionCatalog | null;
  enabled?: boolean;
  onSelectedIdChange?: (geoid: string | null) => void;
};

/**
 * Hybrid map mount. Lane A never receives a B snapshot.
 * Public Signal B stays unpublished unless a later stitch passes lane B.
 */
export function JudgeMap({
  lane,
  historical,
  snapshot = null,
  enabled,
  onSelectedIdChange,
}: JudgeMapProps) {
  const catalog = bindExclusiveMapLayer({
    lane,
    historical,
    snapshot,
  });
  return (
    <MapInteractionStage
      enabled={enabled}
      catalog={catalog}
      onSelectedIdChange={onSelectedIdChange}
    />
  );
}
