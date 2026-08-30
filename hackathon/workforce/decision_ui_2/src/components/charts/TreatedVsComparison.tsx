import type { AnalysisAreaId } from "@/contracts";
import { publicChart } from "@/data/publicSurface";
import { TemporalChart } from "./TemporalChart";

export function TreatedVsComparison({
  selectedAreaId,
}: {
  readonly selectedAreaId: AnalysisAreaId | null;
}) {
  return <TemporalChart model={publicChart("treated_vs_comparison")} selectedAreaId={selectedAreaId} />;
}
