import type { AnalysisJobPayload, AnalysisJobRequest } from "@/api/analysisJobs";
import { useJobStore } from "@/stores/jobStore";
import {
  decision8EvidencePanel,
  decisionThermalLimitation,
  probabilityFieldsPresentation,
  stallCopy,
} from "@/utils/evidencePresentation";
import { jobProgressLabel } from "@/utils/jobPolling";
import { BACKEND_ORDERING_COPY } from "@/utils/mapPresentation";
import type { RankingPresentation } from "@/utils/mapLayer";
import { CopyableToken } from "./CopyableToken";

type DecisionRailViewProps = {
  ranking: RankingPresentation;
  snapshot: AnalysisJobPayload | null;
  busy: boolean;
  canResubmit: boolean;
  stalled: boolean;
  lastRequest: AnalysisJobRequest | null;
  onResubmit: () => void;
};

export function DecisionRailView({
  ranking,
  snapshot,
  busy,
  canResubmit,
  stalled,
  lastRequest,
  onResubmit,
}: DecisionRailViewProps) {
  const isUnknown = snapshot?.status === "unknown_job";
  const thermalLimitation = decisionThermalLimitation({
    status: snapshot?.status,
    limitations: snapshot?.result?.system_limitations,
  });
  const decision8Panel = decision8EvidencePanel(snapshot?.result);
  const probability = probabilityFieldsPresentation(snapshot?.result?.zones);
  const hasLongAnalysis = Boolean(
    decision8Panel || thermalLimitation || probability || snapshot?.result,
  );
  const stall = stallCopy({
    stalled,
    status: snapshot?.status,
    hasResult: snapshot?.result != null,
  });

  return (
    <aside className="decision" aria-label="Decision panel">
      <header className="rail-head">
        <p className="kicker">Decision</p>
        <h2>Evidence</h2>
      </header>

      <p className="evidence-stamp" data-testid="evidence-state">
        {ranking.state}
      </p>
      <p className="decision-copy">
        {ranking.state === "INSUFFICIENT_EVIDENCE"
          ? "No zone ranking is shown until an analysis job completes with enough thermal evidence. Missing data is not treated as safe."
          : BACKEND_ORDERING_COPY}
      </p>
      {hasLongAnalysis && (
        <p className="decision-copy">
          Full evidence, versions, and suppression notes are in Analysis detail
          below.
        </p>
      )}

      <section
        className="job-progress"
        aria-live="polite"
        aria-busy={busy}
        data-testid="job-progress"
      >
        <p className="kicker">Job</p>
        <p className="job-status">
          {busy && <span className="busy-pip" aria-hidden="true" />}
          {jobProgressLabel(snapshot?.status ?? null)}
        </p>
        {snapshot?.job_id && (
          <p className="job-id">
            <span>ID</span>{" "}
            <CopyableToken
              value={snapshot.job_id}
              aria-label="Copy job ID"
              testId="job-id"
            />
          </p>
        )}
        {snapshot?.message && <p className="job-message">{snapshot.message}</p>}
        {stall && (
          <p className="job-message" data-testid="job-stalled">
            {stall.message}
          </p>
        )}
      </section>

      {isUnknown && (
        <section className="recovery" data-testid="unknown-job-recovery">
          <p>
            {snapshot.message ??
              "The analysis job is no longer present on this runtime."}
          </p>
          <p>The last request is still held. Resubmit to start a new job.</p>
          <button
            type="button"
            className="submit-btn"
            data-testid="resubmit-job"
            disabled={!canResubmit || !lastRequest}
            onClick={onResubmit}
          >
            Resubmit
          </button>
        </section>
      )}
      {stall && !isUnknown && (
        <section className="recovery" data-testid="stalled-job-recovery">
          <p>{stall.recoveryHint}</p>
          <button
            type="button"
            className="submit-btn"
            disabled={!canResubmit || !lastRequest}
            onClick={onResubmit}
          >
            Resubmit
          </button>
        </section>
      )}
    </aside>
  );
}

export function DecisionRail({ ranking }: { ranking: RankingPresentation }) {
  const snapshot = useJobStore((state) => state.snapshot);
  const busy = useJobStore((state) => state.busy);
  const canResubmit = useJobStore((state) => state.canResubmit);
  const stalled = useJobStore((state) => state.stalled);
  const resubmit = useJobStore((state) => state.resubmit);
  const lastRequest = useJobStore((state) => state.lastRequest);
  return (
    <DecisionRailView
      ranking={ranking}
      snapshot={snapshot}
      busy={busy}
      canResubmit={canResubmit}
      stalled={stalled}
      lastRequest={lastRequest}
      onResubmit={() => void resubmit()}
    />
  );
}
