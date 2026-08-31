import { analysisAreaLabel } from "@/features/selectedAreaStory/identity";
import type { SelectedAreaDecisionStory } from "@/features/selectedAreaStory/types";
import { CONTEXT_TITLE } from "./copy";

type ContextPanelProps = {
  story: SelectedAreaDecisionStory;
};

export function ContextPanel({ story }: ContextPanelProps) {
  const facts = story.questions.different.facts;
  return (
    <section className="hx-section hx-secondary-panel" data-testid="context-panel" id="context" aria-labelledby="context-title">
      <h2 id="context-title">{CONTEXT_TITLE}</h2>
      <p className="hx-section-lead">
        {analysisAreaLabel(story.identity.geoid) ?? "Select an analysis area"}. Not a score.
      </p>
      {facts.length === 0 ? (
        <p className="hx-missing">Local context for this analysis area is still loading.</p>
      ) : (
        <ul className="hx-cards" data-testid="story-facts">
          {facts.map((fact) => (
            <li key={fact.kind} data-source={fact.sourceFamily} data-comparison={String(fact.comparisonAllowed)}>
              <strong>{fact.label}</strong>
              <span>{fact.sentence}</span>
              {!fact.comparisonAllowed ? (
                <em>Estimate shown with uncertainty. A higher/lower comparison is not published.</em>
              ) : null}
            </li>
          ))}
        </ul>
      )}
    </section>
  );
}
