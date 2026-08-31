import type { PreparednessEvidenceStatus } from "./narrative";
import {
  PREP_DISCLAIMER,
  PREP_IDENTIFIED,
  PREP_NOT_IDENTIFIED,
  PREP_SOURCE_SUMMARY,
  PREP_TITLE,
  PREP_UNKNOWN,
} from "./copy";

type PreparednessPanelProps = {
  status: PreparednessEvidenceStatus;
  sentences: string[];
  sourceLines?: string[];
};

function publicStatus(status: PreparednessEvidenceStatus): string {
  if (status === "IDENTIFIED") {
    return PREP_IDENTIFIED;
  }
  if (status === "NOT_IDENTIFIED_IN_DATASET") {
    return PREP_NOT_IDENTIFIED;
  }
  return PREP_UNKNOWN;
}

export function PreparednessPanel({
  status,
  sentences,
  sourceLines = [],
}: PreparednessPanelProps) {
  return (
    <section
      className="hx-section hx-secondary-panel hx-level-2"
      data-testid="preparedness-panel"
      id="preparedness"
      aria-labelledby="prep-title"
    >
      <h2 id="prep-title">{PREP_TITLE}</h2>
      <p className="hx-status hx-status-large" data-testid="preparedness-status" data-status={status}>
        {publicStatus(status)}
      </p>
      <div data-testid="story-support">
        {sentences.map((line) => (
          <p key={line}>{line}</p>
        ))}
        <p className="hx-note">{PREP_DISCLAIMER}</p>
        {sourceLines.length > 0 ? (
          <details className="hx-method">
            <summary>{PREP_SOURCE_SUMMARY}</summary>
            {sourceLines.map((line) => (
              <p key={line}>{line}</p>
            ))}
          </details>
        ) : null}
      </div>
    </section>
  );
}
