import type { AnalysisAreaId } from "@/contracts";
import { publicChart } from "@/data/publicSurface";
import { TemporalChart } from "./TemporalChart";

export function SeasonalComparison({
  selectedAreaId,
}: {
  readonly selectedAreaId: AnalysisAreaId | null;
}) {
  return <TemporalChart model={publicChart("seasonal_comparison")} selectedAreaId={selectedAreaId} />;
}
