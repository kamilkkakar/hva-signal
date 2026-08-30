import type { SelectedAreaDecisionStory } from "@/features/selectedAreaStory/types";
import { PREP_DISCLAIMER, PREP_TITLE, preparednessLabel } from "./copy";

type PreparednessPanelProps = {
  story: SelectedAreaDecisionStory;
};

export function PreparednessPanel({ story }: PreparednessPanelProps) {
  const support = story.questions.support;
  return (
    <section className="hx-section" data-testid="preparedness-panel" aria-labelledby="prep-title">
      <p className="hx-kicker">Preparedness</p>
      <h2 id="prep-title">{PREP_TITLE}</h2>
      <p className="hx-status" data-testid="preparedness-status">
        {preparednessLabel(support.status)}
      </p>
      <div data-testid="story-support">
        {support.sentences.map((line) => (
          <p key={line}>{line}</p>
        ))}
        <p className="hx-note">{PREP_DISCLAIMER}</p>
      </div>
    </section>
  );
}
