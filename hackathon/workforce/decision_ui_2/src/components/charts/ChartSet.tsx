import type { AnalysisAreaId, ChartKind } from "@/contracts";
import { publicChart } from "@/data/publicSurface";
import { TemporalChart } from "./TemporalChart";

type ChartSetProps = {
  readonly kinds: readonly ChartKind[];
  readonly selectedAreaId: AnalysisAreaId | null;
};

export function ChartSet({ kinds, selectedAreaId }: ChartSetProps) {
  if (kinds.length === 0) {
    return null;
  }
  return (
    <section className="chart-grid" aria-label="Temporal charts" data-testid="chart-set">
      {kinds.map((kind) => (
        <TemporalChart
          key={kind}
          model={publicChart(kind)}
          selectedAreaId={selectedAreaId}
        />
      ))}
    </section>
  );
}
