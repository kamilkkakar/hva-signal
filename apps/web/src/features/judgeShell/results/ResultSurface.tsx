import type { AnalysisJobPayload } from "@/api/analysisJobs";
import { Decision8AccordionView } from "./Decision8Accordion";
import { resultCardsFromSnapshot } from "./presentation";
import { ResultColumn } from "./ResultColumn";
import "./results.css";

export type ResultSurfaceProps = {
  snapshot: AnalysisJobPayload | null;
  rankingState: "INSUFFICIENT_EVIDENCE" | "READY";
  busy?: boolean;
};

/** Isolated overflow harness: map-primary stack. No 260 / 1fr / 300 rail. */
export function ResultSurface({
  snapshot,
  rankingState,
  busy = false,
}: ResultSurfaceProps) {
  const view = resultCardsFromSnapshot({ snapshot, rankingState, busy });
  return (
    <div className="result-overflow-page" data-testid="result-overflow-page">
      <div className="result-map-primary">
        <div className="result-map-slot" data-testid="result-map-slot" aria-hidden="true">
          Map
        </div>
        <ResultColumn view={view} />
        <Decision8AccordionView snapshot={snapshot} />
      </div>
    </div>
  );
}
