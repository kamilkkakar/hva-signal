import type { AnalysisJobPayload, AnalysisResultStub } from "@/api/analysisJobs";
import type { JobStatus } from "@/types";
import { ResultCards, resultCardsFromSnapshot } from "./results";
import "./results/results.css";
import { SignalAPanel } from "./signalA";
import { SignalBUnavailableDisclosure } from "./signalB";

type ThermalBandProps = {
  snapshot: AnalysisJobPayload | null;
  rankingState: "INSUFFICIENT_EVIDENCE" | "READY";
  busy: boolean;
  status: JobStatus | null;
  result: AnalysisResultStub | null;
};

export function ThermalBand({
  snapshot,
  rankingState,
  busy,
  status,
  result,
}: ThermalBandProps) {
  const view = resultCardsFromSnapshot({ snapshot, rankingState, busy });
  return (
    <section className="judge-thermal" aria-label="Thermal evidence">
      <ResultCards view={view} />
      <SignalAPanel
        status={status}
        result={result}
        requested={snapshot != null}
      />
      <SignalBUnavailableDisclosure />
    </section>
  );
}
