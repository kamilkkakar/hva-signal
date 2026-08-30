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

/** Isolated overflow harness: 3-col grid + full-width Decision 8 accordion. */
export function ResultSurface({
  snapshot,
  rankingState,
  busy = false,
}: ResultSurfaceProps) {
  const view = resultCardsFromSnapshot({ snapshot, rankingState, busy });
  return (
    <div className="result-overflow-page" data-testid="result-overflow-page">
      <div className="result-overflow-grid">
        <aside className="result-overflow-stub" aria-hidden="true">
          Query
        </aside>
        <div className="result-overflow-stub" aria-hidden="true">
          Map
        </div>
        <ResultColumn view={view} />
        <Decision8AccordionView snapshot={snapshot} />
      </div>
    </div>
  );
}
