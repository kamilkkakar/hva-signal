import type { AnalysisResultStub } from "@/api/analysisJobs";
import type { JobStatus } from "@/types";
import {
  ACTION_BAND_KICKER,
  ACTION_V0_TITLE,
  DOES_NOT_COLUMN_LABEL,
  SUPPORTS_COLUMN_LABEL,
} from "./copy";
import { presentActionFraming } from "./framing";
import "./action.css";

export type ActionFramingProps = {
  status?: JobStatus | null;
  result?: AnalysisResultStub | null;
};

export type ActionSupportsBandProps = ActionFramingProps;

/** Hybrid slot 7: what this evidence supports / does not establish. */
export function ActionSupportsBand({ status, result }: ActionSupportsBandProps) {
  const view = presentActionFraming({ status, result });

  return (
    <section
      className="action-supports-band"
      data-testid="action-v0"
      data-action-kind={view.kind}
      data-hybrid-slot="supports-does-not"
      aria-label={ACTION_V0_TITLE}
    >
      <header className="action-supports-head">
        <p className="kicker">{ACTION_BAND_KICKER}</p>
        <h3>{ACTION_V0_TITLE}</h3>
        <p className="action-status" data-testid="action-v0-status">
          {view.status}
        </p>
        <p className="action-scope" data-testid="action-v0-scope">
          {view.scope}
        </p>
      </header>
      <p
        className="evidence-stamp"
        data-testid="action-v0-stamp"
        data-action-kind={view.kind}
      >
        {view.stamp}
      </p>
      <p className="action-says" data-testid="action-v0-says">
        {view.says}
      </p>
      <dl className="action-supports-grid">
        <div>
          <dt>{SUPPORTS_COLUMN_LABEL}</dt>
          <dd data-testid="action-v0-supports">{view.supports}</dd>
        </div>
        <div>
          <dt>{DOES_NOT_COLUMN_LABEL}</dt>
          <dd data-testid="action-v0-does-not">{view.doesNotEstablish}</dd>
        </div>
      </dl>
    </section>
  );
}

/** ACT-A name. Same Hybrid band — not a Decision-rail card. */
export const ActionFraming = ActionSupportsBand;
