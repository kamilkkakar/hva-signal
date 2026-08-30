import type { AnalysisAreaId } from "@/contracts";
import { publicChart } from "@/data/publicSurface";
import { TemporalChart } from "./TemporalChart";

export function HourlyCurve({ selectedAreaId }: { readonly selectedAreaId: AnalysisAreaId | null }) {
  return <TemporalChart model={publicChart("hourly_curve")} selectedAreaId={selectedAreaId} />;
}
