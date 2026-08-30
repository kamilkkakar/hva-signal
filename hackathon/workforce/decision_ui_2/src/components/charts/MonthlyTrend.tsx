import type { AnalysisAreaId } from "@/contracts";
import { publicChart } from "@/data/publicSurface";
import { TemporalChart } from "./TemporalChart";

export function MonthlyTrend({ selectedAreaId }: { readonly selectedAreaId: AnalysisAreaId | null }) {
  return <TemporalChart model={publicChart("monthly_trend")} selectedAreaId={selectedAreaId} />;
}
