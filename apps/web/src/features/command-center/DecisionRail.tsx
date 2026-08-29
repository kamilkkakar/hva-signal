import { useJobStore } from "@/stores/jobStore";
import {
  decision8EvidencePanel,
  decisionThermalLimitation,
  evidenceGraphPresentation,
  probabilityFieldsPresentation,
  stallCopy,
} from "@/utils/evidencePresentation";
import { jobProgressLabel } from "@/utils/jobPolling";
import type { RankingPresentation } from "@/utils/mapLayer";

type DecisionRailProps = {
  ranking: RankingPresentation;
};

export function DecisionRail({ ranking }: DecisionRailProps) {
  const snapshot = useJobStore((state) => state.snapshot);
  const busy = useJobStore((state) => state.busy);
  const canResubmit = useJobStore((state) => state.canResubmit);
  const stalled = useJobStore((state) => state.stalled);
  const resubmit = useJobStore((state) => state.resubmit);
  const lastRequest = useJobStore((state) => state.lastRequest);

  const isUnknown = snapshot?.status === "unknown_job";
  const graph = evidenceGraphPresentation(snapshot?.result);
  const probability = probabilityFieldsPresentation(snapshot?.result?.zones);
  const thermalLimitation = decisionThermalLimitation({
    status: snapshot?.status,
    limitations: snapshot?.result?.system_limitations,
  });
  const decision8Panel = decision8EvidencePanel(snapshot?.result);
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
          : "Analysis returned ranked zones. Geometry and decision cards are not wired yet, so no choropleth is drawn."}
      </p>

      <section className="evidence-detail">
        {thermalLimitation && (
          <p
            className="decision-limitation"
            data-testid="decision-thermal-limitation"
          >
            {thermalLimitation}
          </p>
        )}

        {decision8Panel && (
          <section
            className="decision-copy"
            data-testid="decision8-evidence-panel"
          >
            <p>{decision8Panel.title}</p>
            <p data-testid="decision8-observed-s">
              Observed normalized spread S: {decision8Panel.observedSpread}
            </p>
            <p data-testid="decision8-policy-floor">
              Decision 8 policy floor: {decision8Panel.floorDisplay}
            </p>
            <p>Statistic: {decision8Panel.statistic}</p>
            <p>Tail group size: {decision8Panel.tailGroupSize}</p>
            <p data-testid="decision8-policy-version">
              Decision 8 policy: {decision8Panel.policyVersion}
            </p>
            <p data-testid="decision8-reference-version">
              Decision 1B reference: {decision8Panel.referenceVersion}
            </p>
            <p data-testid="decision8-zone-geometry">
              Zone geometry: {decision8Panel.zoneGeometryVersion}
            </p>
            <p>
              Historical years / hour:{" "}
              {decision8Panel.historicalYears?.join(", ") ?? "unavailable"} /{" "}
              {decision8Panel.referenceHour ?? "unavailable"}
            </p>
            <p>Reference quality: {decision8Panel.referenceQuality}</p>
            <p>Result: {decision8Panel.result}</p>
            {decision8Panel.reason && (
              <p data-testid="decision8-suppression-reason">
                Reason thermal ranking was suppressed: {decision8Panel.reason}
              </p>
            )}
          </section>
        )}

        <p className="evidence-stamp" data-testid="evidence-graph-state">
          {graph.state}
        </p>
        <p className="decision-copy">{graph.copy}</p>

        {probability && (
          <p className="decision-copy" data-testid="probability-blocked">
            {probability.label}
          </p>
        )}
      </section>

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
            <span>ID</span> {snapshot.job_id}
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
            onClick={() => void resubmit()}
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
            onClick={() => void resubmit()}
          >
            Resubmit
          </button>
        </section>
      )}
    </aside>
  );
}
