import { COPE_QUESTION, KICKER, PANEL_ARIA, VERIFY_QUESTION } from "./copy";
import type { AreaContextPanelView } from "./present";

export type AreaContextPanelProps = {
  view: AreaContextPanelView;
};

export function AreaContextPanel({ view }: AreaContextPanelProps) {
  return (
    <article
      className="area-context-panel"
      aria-label={PANEL_ARIA}
      data-testid="area-context-panel"
    >
      <p className="kicker">{KICKER}</p>
      <h2 data-testid="area-context-label">{view.areaLabel}</h2>
      <p data-testid="area-context-tract">Census tract {view.tractId}</p>
      <p data-testid="area-context-not-score">{view.notAScore}</p>
      <p data-testid="area-context-score-refusal">{view.scoreRefusal}</p>
      {view.thermalStatus === "UNKNOWN" ? (
        <p data-testid="area-context-thermal">THERMAL EVIDENCE: UNKNOWN</p>
      ) : null}
      <section aria-label={COPE_QUESTION}>
        <h3>{COPE_QUESTION}</h3>
        {view.cope.length ? (
          view.cope.map((line) => <p key={line}>{line}</p>)
        ) : (
          <ul>
            {view.facts.map((fact) => (
              <li key={fact.label}>{fact.sentence}</li>
            ))}
          </ul>
        )}
      </section>
      <ul data-testid="area-context-facts">
        {view.facts.map((fact) => (
          <li key={fact.label} data-comparison-allowed={String(fact.comparisonAllowed)}>
            <strong>{fact.label}.</strong> {fact.sentence}
          </li>
        ))}
      </ul>
      <section aria-label="Preparedness">
        <h3>Preparedness</h3>
        {view.preparedness.map((line) => (
          <p key={line}>{line}</p>
        ))}
      </section>
      {view.uncertainty.length ? (
        <section aria-label="Uncertainty">
          <h3>Uncertainty</h3>
          {view.uncertainty.map((line) => (
            <p key={line}>{line}</p>
          ))}
        </section>
      ) : null}
      <section aria-label={VERIFY_QUESTION}>
        <h3>{VERIFY_QUESTION}</h3>
        <ol data-testid="area-context-direction">
          {view.direction.map((line) => (
            <li key={line}>{line}</li>
          ))}
        </ol>
      </section>
    </article>
  );
}
