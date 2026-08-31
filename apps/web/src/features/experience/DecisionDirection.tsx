import type { SelectedAreaDecisionStory } from "@/features/selectedAreaStory/types";
import {
  DECISION_MATTERS,
  DECISION_NEXT,
  DECISION_NO_RECOMMENDATION,
  DECISION_SHOWS,
  DECISION_TITLE,
  RANKING_WITHHELD_BODY,
  RANKING_WITHHELD_NEXT,
} from "./copy";

type DecisionDirectionProps = {
  story: SelectedAreaDecisionStory;
  rankingWithheld: boolean;
};

export function DecisionDirection({ story, rankingWithheld }: DecisionDirectionProps) {
  const shows = rankingWithheld
    ? RANKING_WITHHELD_BODY
    : story.questions.thermal.a.kind === "order_shown"
      ? "A historical 03:00 comparison is available for this analysis area. It is comparative evidence, not a treatment rank."
      : "Thermal evidence for this analysis area is limited to the cached observation and temporal series.";
  const matters = rankingWithheld
    ? RANKING_WITHHELD_NEXT
    : "Local context and preparedness help decide what to inspect on the ground. They do not create a hidden heat score.";
  const next = story.questions.verify.rules.map((rule) => rule.text);

  return (
    <section className="hx-section hx-decision" data-testid="decision-direction" aria-labelledby="decision-title">
      <h2 id="decision-title">{DECISION_TITLE}</h2>
      <div className="hx-decision-grid">
        <article>
          <h3>{DECISION_SHOWS}</h3>
          <p data-testid="decision-shows">{shows}</p>
        </article>
        <article>
          <h3>{DECISION_MATTERS}</h3>
          <p data-testid="decision-matters">{matters}</p>
        </article>
        <article>
          <h3>{DECISION_NEXT}</h3>
          <ul data-testid="decision-next">
            {next.length ? next.map((line) => <li key={line}>{line}</li>) : (
              <li>Verify local cooling access, shade, housing exposure, and whether more thermal evidence is needed.</li>
            )}
          </ul>
        </article>
      </div>
      <p className="hx-note">{DECISION_NO_RECOMMENDATION}</p>
    </section>
  );
}
