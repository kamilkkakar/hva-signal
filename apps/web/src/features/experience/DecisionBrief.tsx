import type { NarrativeSynthesis } from "./narrative";
import {
  BRIEF_EVIDENCE,
  BRIEF_KICKER,
  BRIEF_NEXT,
  BRIEF_TITLE,
  BRIEF_WHY,
  DECISION_NO_RECOMMENDATION,
} from "./copy";

type DecisionBriefProps = {
  synthesis: NarrativeSynthesis;
  areaLabel: string | null;
};

/** Post-map guided brief: evidence → why → suggested direction (after glanceable °C). */
export function DecisionBrief({ synthesis, areaLabel }: DecisionBriefProps) {
  const evidence = synthesis.whatEvidenceShows.slice(0, 3);
  const why = synthesis.whyItMatters.slice(0, 2);
  const next = synthesis.verifyNext.slice(0, 3);

  return (
    <section
      className="hx-section hx-decision-brief hx-level-1"
      id="brief"
      data-testid="decision-brief"
      aria-labelledby="decision-brief-title"
      data-pattern={synthesis.dominantPattern}
    >
      <p className="hx-kicker">{BRIEF_KICKER}</p>
      <h2 id="decision-brief-title">{BRIEF_TITLE}</h2>
      <p className="hx-section-lead" data-testid="decision-brief-lead">
        {areaLabel ?? "Selected analysis area"} · {synthesis.patternTitle}
      </p>
      <aside className="hx-pattern-card" data-testid="evidence-pattern" aria-label="Evidence pattern">
        <p className="hx-pattern-title" data-testid="evidence-pattern-title">
          {synthesis.patternTitle}
        </p>
        {synthesis.patternSummary ? (
          <p className="hx-pattern-summary" data-testid="decision-brief-summary">
            {synthesis.patternSummary}
          </p>
        ) : null}
      </aside>
      {synthesis.evidenceSummary.length > 0 ? (
        <div className="hx-evidence-signals" data-testid="evidence-summary" aria-label="Evidence summary">
          <ul data-testid="evidence-summary-signals">
            {synthesis.evidenceSummary.map((signal) => (
              <li key={signal.id} data-signal={signal.id}>
                <span className="hx-signal-label">{signal.label}</span>
                <strong className="hx-signal-value">{signal.value}</strong>
              </li>
            ))}
          </ul>
        </div>
      ) : null}
      <div className="hx-brief-grid">
        <article>
          <h3>{BRIEF_EVIDENCE}</h3>
          <ul data-testid="brief-evidence">
            {evidence.map((line) => (
              <li key={line}>{line}</li>
            ))}
          </ul>
        </article>
        <article>
          <h3>{BRIEF_WHY}</h3>
          <ul data-testid="brief-why">
            {why.map((line) => (
              <li key={line}>{line}</li>
            ))}
          </ul>
        </article>
        <article>
          <h3>{BRIEF_NEXT}</h3>
          <ul data-testid="brief-next">
            {next.map((line) => (
              <li key={line}>{line}</li>
            ))}
          </ul>
          <p className="hx-guided-next">
            <a href="#verify">Full investigation checklist</a>
            {" · "}
            <a href="#changed">Matched nighttime</a>
            {" · "}
            <a href="#context">Local context</a>
          </p>
        </article>
      </div>
      <p className="hx-note hx-disclaimer-compact">{DECISION_NO_RECOMMENDATION}</p>
    </section>
  );
}
