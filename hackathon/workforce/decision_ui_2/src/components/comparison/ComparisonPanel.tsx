import type { AnalysisArea, AnalysisAreaId } from "@/contracts";
import { COMPARISON_PICK, TEMPORAL_PENDING } from "@/ia/copy";
import { PendingState } from "@/components/pending/PendingState";

type ComparisonPanelProps = {
  readonly areas: readonly AnalysisArea[];
  readonly selectedAreaId: AnalysisAreaId | null;
  readonly compareAreaId: AnalysisAreaId | null;
  readonly onCompare: (id: AnalysisAreaId | null) => void;
};

export function ComparisonPanel({
  areas,
  selectedAreaId,
  compareAreaId,
  onCompare,
}: ComparisonPanelProps) {
  return (
    <section className="compare-panel" aria-label="Comparison" data-testid="comparison-panel">
      <h3>Compare analysis areas</h3>
      <dl className="meta-row">
        <div>
          <dt>Focus</dt>
          <dd>
            {selectedAreaId
              ? (areas.find((area) => area.id === selectedAreaId)?.primaryLabel ?? selectedAreaId)
              : "None selected"}
          </dd>
        </div>
        <div>
          <dt>Peer</dt>
          <dd>
            <label>
              <span className="sr-only">Peer analysis area</span>
              <select
                value={compareAreaId ?? ""}
                onChange={(event) =>
                  onCompare(event.target.value ? (event.target.value as AnalysisAreaId) : null)
                }
                data-testid="compare-select"
              >
                <option value="">None</option>
                {areas.map((area) => (
                  <option key={area.id} value={area.id}>
                    {area.primaryLabel}
                  </option>
                ))}
              </select>
            </label>
          </dd>
        </div>
      </dl>
      <p className="area-once">{COMPARISON_PICK}</p>
      <PendingState message={TEMPORAL_PENDING} testId="comparison-pending" />
    </section>
  );
}
