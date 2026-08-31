import { analysisAreaLabel } from "@/features/selectedAreaStory/identity";
import type { ContextComparison } from "./narrative";
import { CONTEXT_LEAD, CONTEXT_TITLE } from "./copy";

type ContextPanelProps = {
  comparisons: ContextComparison[];
  selectedZoneId: string | null;
};

export function ContextPanel({ comparisons, selectedZoneId }: ContextPanelProps) {
  return (
    <section
      className="hx-section hx-secondary-panel hx-level-2"
      data-testid="context-panel"
      id="context"
      aria-labelledby="context-title"
    >
      <h2 id="context-title">{CONTEXT_TITLE}</h2>
      <p className="hx-section-lead">
        {analysisAreaLabel(selectedZoneId) ?? "Select an analysis area"}. {CONTEXT_LEAD}
      </p>
      {comparisons.length === 0 ? (
        <p className="hx-missing">Local context for this analysis area is still loading.</p>
      ) : (
        <ul className="hx-cards hx-number-cards" data-testid="story-facts">
          {comparisons.map((fact) => (
            <li
              key={fact.kind}
              data-kind={fact.kind}
              data-comparison={String(fact.comparisonAllowed)}
              data-tone={fact.tone}
            >
              <div className="hx-card-stack">
                <strong className="hx-card-value" data-testid={`context-value-${fact.kind}`}>
                  {fact.valueDisplay}
                </strong>
                <span className="hx-card-label">{fact.label}</span>
              </div>
              {fact.comparisonAllowed && fact.comparison ? (
                <span className="hx-card-cmp">
                  {fact.comparison === "higher"
                    ? "Above median"
                    : fact.comparison === "lower"
                      ? "Below median"
                      : "Near median"}
                </span>
              ) : (
                <em>Uncertainty published; no higher/lower call.</em>
              )}
            </li>
          ))}
        </ul>
      )}
    </section>
  );
}
