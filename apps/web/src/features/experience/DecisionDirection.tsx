import type { NarrativeSynthesis } from "./narrative";
import { DECISION_MATTERS, DECISION_NEXT, DECISION_NO_RECOMMENDATION, DECISION_SHOWS, DECISION_TITLE } from "./copy";

type DecisionDirectionProps = {
  synthesis: NarrativeSynthesis;
  areaLabel: string | null;
};

export function DecisionDirection({ synthesis, areaLabel }: DecisionDirectionProps) {
  return (
    <section
      className="hx-section hx-decision hx-level-1"
      id="verify"
      data-testid="decision-direction"
      aria-labelledby="decision-title"
      data-pattern={synthesis.dominantPattern}
    >
      <h2 id="decision-title">{DECISION_TITLE}</h2>
      <p className="hx-section-lead">
        {areaLabel ?? "Selected analysis area"} · {synthesis.patternTitle}
      </p>
      <div className="hx-decision-grid">
        <article>
          <h3>{DECISION_SHOWS}</h3>
          <ul data-testid="decision-shows">
            {synthesis.whatEvidenceShows.map((line) => (
              <li key={line}>{line}</li>
            ))}
          </ul>
        </article>
        <article>
          <h3>{DECISION_MATTERS}</h3>
          <ul data-testid="decision-matters">
            {synthesis.whyItMatters.map((line) => (
              <li key={line}>{line}</li>
            ))}
          </ul>
        </article>
        <article>
          <h3>{DECISION_NEXT}</h3>
          <ul data-testid="decision-next">
            {synthesis.verifyNext.map((line) => (
              <li key={line}>{line}</li>
            ))}
          </ul>
        </article>
      </div>
      <p className="hx-note hx-disclaimer-compact">{DECISION_NO_RECOMMENDATION}</p>
    </section>
  );
}
