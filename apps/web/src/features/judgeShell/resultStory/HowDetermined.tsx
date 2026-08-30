import {
  HOW_FLOOR_LABEL,
  HOW_SEPARATION_LABEL,
  HOW_SUMMARY,
} from "./copy";
import type { HowDeterminedView } from "./types";

export type HowDeterminedProps = {
  how: HowDeterminedView;
};

/** Story-chrome accordion. Deep policy / geometry / job IDs stay with RESCUE-I. */
export function HowDetermined({ how }: HowDeterminedProps) {
  return (
    <details className="result-story-how" data-testid="result-story-how">
      <summary className="result-story-how-summary">{HOW_SUMMARY}</summary>
      <dl className="result-story-how-body">
        <div>
          <dt className="judge-sr">Historical comparison</dt>
          <dd data-testid="result-story-how-history">{how.historicalComparison}</dd>
        </div>
        <div>
          <dt className="judge-sr">Spatial differentiation</dt>
          <dd data-testid="result-story-how-differentiation">
            {how.spatialDifferentiation}
          </dd>
        </div>
        {how.observedSeparation != null && (
          <div>
            <dt>{HOW_SEPARATION_LABEL}</dt>
            <dd data-testid="result-story-separation">{how.observedSeparation}</dd>
          </div>
        )}
        {how.minimumSeparation != null && (
          <div>
            <dt>{HOW_FLOOR_LABEL}</dt>
            <dd data-testid="result-story-floor">{how.minimumSeparation}</dd>
          </div>
        )}
      </dl>
    </details>
  );
}
