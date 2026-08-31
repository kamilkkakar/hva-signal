import { analysisAreaLabel } from "@/features/selectedAreaStory/identity";
import type { ContextComparison } from "./narrative";
import { CONTEXT_TITLE } from "./copy";

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
        {analysisAreaLabel(selectedZoneId) ?? "Select an analysis area"}. Context can strengthen,
        weaken, or complicate the thermal reading — not a score.
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
              <strong className="hx-card-value" data-testid={`context-value-${fact.kind}`}>
                {fact.valueDisplay}
              </strong>
              <span className="hx-card-label">{fact.label}</span>
              {fact.comparisonAllowed && fact.comparison ? (
                <span className="hx-card-cmp">
                  {fact.comparison === "higher"
                    ? "Above analysis-geography median"
                    : fact.comparison === "lower"
                      ? "Below analysis-geography median"
                      : "Similar to analysis-geography median"}
                </span>
              ) : (
                <em>Estimate shown with uncertainty. A higher/lower comparison is not published.</em>
              )}
              {fact.interpretation ? (
                <span className="hx-card-interpret">{fact.interpretation}</span>
              ) : null}
            </li>
          ))}
        </ul>
      )}
    </section>
  );
}
