import type { AnalysisJobPayload, AnalysisResultStub } from "@/api/analysisJobs";
import type { JobStatus } from "@/types";
import { SignalAPanel } from "./signalA";
import { SignalBUnavailableDisclosure } from "./signalB";

type ThermalBandProps = {
  snapshot: AnalysisJobPayload | null;
  status: JobStatus | null;
  result: AnalysisResultStub | null;
};

export function ThermalBand({ snapshot, status, result }: ThermalBandProps) {
  return (
    <section className="judge-thermal" aria-label="Thermal evidence">
      <SignalAPanel
        status={status}
        result={result}
        requested={snapshot != null}
      />
      <SignalBUnavailableDisclosure />
    </section>
  );
}
