import type { AnalysisJobPayload, AnalysisResultStub } from "@/api/analysisJobs";
import type { JobStatus } from "@/types";
import { SignalAPanel } from "./signalA";
import { SignalBUnavailableDisclosure } from "./signalB";

type ThermalBandProps = {
  snapshot: AnalysisJobPayload | null;
  status: JobStatus | null;
  result: AnalysisResultStub | null;
  selectedZoneId?: string | null;
};

export function ThermalBand({
  snapshot,
  status,
  result,
  selectedZoneId = null,
}: ThermalBandProps) {
  return (
    <section className="judge-thermal" aria-label="Thermal evidence">
      <SignalAPanel
        status={status}
        result={result}
        requested={snapshot != null}
        selectedZoneId={selectedZoneId}
      />
      <SignalBUnavailableDisclosure />
    </section>
  );
}
