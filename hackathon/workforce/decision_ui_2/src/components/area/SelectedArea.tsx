import type { AnalysisArea, AnalysisAreaId } from "@/contracts";
import { GEOID_SECONDARY, SELECTED_HINT, SELECTED_NONE } from "@/ia/copy";

type SelectedAreaProps = {
  readonly areas: readonly AnalysisArea[];
  readonly selectedAreaId: AnalysisAreaId | null;
};

export function SelectedArea({ areas, selectedAreaId }: SelectedAreaProps) {
  const area = areas.find((item) => item.id === selectedAreaId) ?? null;
  return (
    <section className="area-panel" aria-label="Selected analysis area" data-testid="selected-area">
      <h3>Selected analysis area</h3>
      {area ? (
        <>
          <p className="story-magnitude" data-pending="true">
            {area.primaryLabel}
          </p>
          <dl className="meta-row">
            <div>
              <dt>Primary</dt>
              <dd>{area.primaryLabel}</dd>
            </div>
            <div>
              <dt>Secondary</dt>
              <dd>
                {area.censusTractGeoid
                  ? `Census tract GEOID ${area.censusTractGeoid}`
                  : "Census tract GEOID not bound on this surface."}
              </dd>
            </div>
          </dl>
          <p className="area-once">{GEOID_SECONDARY}</p>
        </>
      ) : (
        <p className="pending">{SELECTED_NONE}</p>
      )}
      <p className="area-once">{SELECTED_HINT}</p>
    </section>
  );
}
