import type { AnalysisAreaId } from "@/contracts";
import { publicChart } from "@/data/publicSurface";
import { TemporalChart } from "./TemporalChart";

export function PersistenceChart({
  selectedAreaId,
}: {
  readonly selectedAreaId: AnalysisAreaId | null;
}) {
  return <TemporalChart model={publicChart("persistence")} selectedAreaId={selectedAreaId} />;
}
