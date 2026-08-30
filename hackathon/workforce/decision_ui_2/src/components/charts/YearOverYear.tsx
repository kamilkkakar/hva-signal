import type { AnalysisAreaId } from "@/contracts";
import { publicChart } from "@/data/publicSurface";
import { TemporalChart } from "./TemporalChart";

export function YearOverYear({ selectedAreaId }: { readonly selectedAreaId: AnalysisAreaId | null }) {
  return <TemporalChart model={publicChart("year_over_year")} selectedAreaId={selectedAreaId} />;
}
