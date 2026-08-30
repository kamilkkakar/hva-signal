import type { AnalysisJobPayload } from "@/api/analysisJobs";
import {
  HOW_DETERMINED_TITLE,
  HOW_LABEL_HISTORICAL,
  HOW_LABEL_POLICY,
  HOW_LABEL_SEPARATION,
  HOW_LABEL_SPATIAL,
} from "./disclosureCopy";
import { howDeterminedFromJob } from "./determination";
import "./disclosure.css";

export type HowDeterminedProps = {
  snapshot: AnalysisJobPayload | null;
};

export function HowDetermined({ snapshot }: HowDeterminedProps) {
  const view = howDeterminedFromJob(snapshot);
  if (view == null) {
    return null;
  }

  return (
    <section
      className="how-determined"
      data-testid="how-this-was-determined"
      aria-label={HOW_DETERMINED_TITLE}
    >
      <h2 className="how-determined-title">{HOW_DETERMINED_TITLE}</h2>
      <dl className="how-determined-list">
        <div>
          <dt>{HOW_LABEL_HISTORICAL}</dt>
          <dd data-testid="how-determined-historical">{view.historicalComparison}</dd>
        </div>
        <div>
          <dt>{HOW_LABEL_SPATIAL}</dt>
          <dd data-testid="how-determined-spatial">{view.spatialDifferentiation}</dd>
        </div>
        <div>
          <dt>{HOW_LABEL_SEPARATION}</dt>
          <dd data-testid="how-determined-separation" data-precision="public-4">
            {view.observedSeparation}
          </dd>
        </div>
        <div>
          <dt>{HOW_LABEL_POLICY}</dt>
          <dd data-testid="how-determined-policy">{view.policyRequirement}</dd>
        </div>
      </dl>
    </section>
  );
}
