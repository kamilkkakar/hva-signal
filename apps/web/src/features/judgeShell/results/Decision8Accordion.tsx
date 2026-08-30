import type { AnalysisJobPayload } from "@/api/analysisJobs";
import { CopyableToken } from "@/features/command-center/CopyableToken";
import { useJobStore } from "@/stores/jobStore";
import {
  decision8EvidencePanel,
  decisionThermalLimitation,
  evidenceGraphPresentation,
  probabilityFieldsPresentation,
} from "@/utils/evidencePresentation";
import { D8_METHOD_NOTE, D8_SUMMARY } from "./copy";

export function Decision8AccordionView({
  snapshot,
}: {
  snapshot: AnalysisJobPayload | null;
}) {
  const graph = evidenceGraphPresentation(snapshot?.result);
  const probability = probabilityFieldsPresentation(snapshot?.result?.zones);
  const thermalLimitation = decisionThermalLimitation({
    status: snapshot?.status,
    limitations: snapshot?.result?.system_limitations,
  });
  const decision8Panel = decision8EvidencePanel(snapshot?.result);
  const hasLongAnalysis = Boolean(
    decision8Panel || thermalLimitation || probability || snapshot?.result,
  );

  return (
    <details
      className="result-d8 analysis-detail"
      data-testid="analysis-detail"
      open={hasLongAnalysis}
    >
      <summary className="result-d8-summary analysis-detail-summary">{D8_SUMMARY}</summary>
      <div className="result-d8-body analysis-detail-body">
        <p className="result-d8-method" data-testid="result-method">
          {D8_METHOD_NOTE}
        </p>
        {thermalLimitation && (
          <p
            className="result-d8-limitation decision-limitation"
            data-testid="decision-thermal-limitation"
          >
            {thermalLimitation}
          </p>
        )}

        {decision8Panel && (
          <section
            className="result-d8-panel analysis-detail-panel"
            data-testid="decision8-evidence-panel"
          >
            <p>{decision8Panel.title}</p>
            <p data-testid="decision8-observed-s">
              Observed normalized spread S: {decision8Panel.observedSpread}
            </p>
            <p data-testid="decision8-policy-floor">
              Decision 8 policy floor: {decision8Panel.floorDisplay}
            </p>
            <p>
              Statistic:{" "}
              <CopyableToken
                value={decision8Panel.statistic}
                aria-label="Copy Decision 8 statistic"
                testId="decision8-statistic"
              />
            </p>
            <p>Tail group size: {decision8Panel.tailGroupSize}</p>
            <p data-testid="decision8-policy-version">
              Decision 8 policy:{" "}
              <CopyableToken
                value={decision8Panel.policyVersion}
                aria-label="Copy Decision 8 policy version"
                testId="decision8-policy-token"
              />
            </p>
            <p data-testid="decision8-reference-version">
              Decision 1B reference:{" "}
              <CopyableToken
                value={decision8Panel.referenceVersion ?? "unavailable"}
                aria-label="Copy Decision 1B reference version"
                testId="decision8-reference-token"
              />
            </p>
            <p data-testid="decision8-zone-geometry">
              Zone geometry:{" "}
              <CopyableToken
                value={decision8Panel.zoneGeometryVersion ?? "unavailable"}
                aria-label="Copy zone geometry version"
                testId="decision8-geometry-token"
              />
            </p>
            <p>
              Historical years / hour:{" "}
              {decision8Panel.historicalYears?.join(", ") ?? "unavailable"} /{" "}
              {decision8Panel.referenceHour ?? "unavailable"}
            </p>
            <p>Reference quality: {decision8Panel.referenceQuality}</p>
            <p>
              Result:{" "}
              <CopyableToken
                value={decision8Panel.result}
                aria-label="Copy Decision 8 result"
                testId="decision8-result"
              />
            </p>
            {decision8Panel.reason && (
              <p data-testid="decision8-suppression-reason">
                Reason thermal ranking was suppressed: {decision8Panel.reason}
              </p>
            )}
            {snapshot?.job_id && (
              <p data-testid="result-d8-job-id">
                Job ID:{" "}
                <CopyableToken
                  value={snapshot.job_id}
                  aria-label="Copy job ID"
                  testId="job-id"
                />
              </p>
            )}
          </section>
        )}

        <p className="result-card-stamp evidence-stamp" data-testid="evidence-graph-state">
          {graph.state}
        </p>
        <p className="result-d8-copy decision-copy">{graph.copy}</p>

        {probability && (
          <p className="result-d8-copy decision-copy" data-testid="probability-blocked">
            {probability.label}
          </p>
        )}
      </div>
    </details>
  );
}

export function Decision8Accordion() {
  const snapshot = useJobStore((state) => state.snapshot);
  return <Decision8AccordionView snapshot={snapshot} />;
}
