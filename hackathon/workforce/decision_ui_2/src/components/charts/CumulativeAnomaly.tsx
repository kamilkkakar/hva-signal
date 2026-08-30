import type { AnalysisAreaId } from "@/contracts";
import { publicChart } from "@/data/publicSurface";
import { TemporalChart } from "./TemporalChart";

export function CumulativeAnomaly({
  selectedAreaId,
}: {
  readonly selectedAreaId: AnalysisAreaId | null;
}) {
  return <TemporalChart model={publicChart("cumulative_anomaly")} selectedAreaId={selectedAreaId} />;
}
