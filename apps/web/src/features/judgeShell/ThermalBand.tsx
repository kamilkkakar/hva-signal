import type { AnalysisJobPayload, AnalysisResultStub } from "@/api/analysisJobs";
import type { JobStatus } from "@/types";
import { SignalAPanel } from "./signalA";
import { SignalBCachedPanel } from "./signalB/SignalBCachedPanel";
import { SignalBUnavailableDisclosure } from "./signalB";
import { PUBLIC_SIGNAL_B } from "./signalB/publicBGate";

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
      <details>
        <summary>Historical comparison method</summary>
        <SignalAPanel
          status={status}
          result={result}
          requested={snapshot != null}
          selectedZoneId={selectedZoneId}
        />
      </details>
      {PUBLIC_SIGNAL_B ? (
        <SignalBCachedPanel selectedZoneId={selectedZoneId} showMap={false} />
      ) : (
        <SignalBUnavailableDisclosure />
      )}
    </section>
  );
}
