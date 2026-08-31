import type { SelectedAreaDecisionStory } from "@/features/selectedAreaStory/types";
import { analysisAreaLabel } from "@/features/selectedAreaStory/identity";
import { formatTempC } from "./format";
import {
  DECISION_MATTERS,
  DECISION_NEXT,
  DECISION_NO_RECOMMENDATION,
  DECISION_SHOWS,
  DECISION_TITLE,
  preparednessLabel,
} from "./copy";

type DecisionDirectionProps = {
  story: SelectedAreaDecisionStory;
  rankingWithheld: boolean;
  temperatureC: number | null;
  change2024vs2022: number | null;
};

export function DecisionDirection({
  story,
  rankingWithheld,
  temperatureC,
  change2024vs2022,
}: DecisionDirectionProps) {
  const area = analysisAreaLabel(story.identity.geoid) ?? "This analysis area";
  const canopy = story.questions.different.facts.find((fact) => fact.kind === "canopy_cover_share");
  const prep = story.questions.support;

  const showsParts = [
    rankingWithheld
      ? "Spatial ranking is withheld because differences across the 25 analysis areas are too small for a defensible order."
      : story.questions.thermal.a.kind === "order_shown"
        ? "A historical 03:00 comparison is available for this analysis area."
        : null,
    temperatureC != null
      ? `${area} reads ${formatTempC(temperatureC)} at the cached 2025-07-15 03:00 observation.`
      : null,
    change2024vs2022 != null
      ? `Matched 03:00 nights warmed ${change2024vs2022 >= 0 ? "+" : ""}${change2024vs2022.toFixed(2)} °C from 2022 to 2024 for this area.`
      : null,
    canopy ? canopy.sentence : null,
  ].filter(Boolean);

  const mattersParts = [
    prep.status === "NOT_IDENTIFIED_IN_DATASET"
      ? "This analysis area has no row in the regional cooling inventory — verify on-the-ground access before assuming absence."
      : prep.status === "IDENTIFIED"
        ? "Inventory rows suggest identified support — confirm hours, capacity, and reach on the ground."
        : "Preparedness status is unknown in this dataset — field verification is required.",
    rankingWithheld
      ? "Do not recreate a hidden thermal ranking from subtle map color alone."
      : "Use comparative evidence alongside absolute °C and local context.",
  ];

  const next = story.questions.verify.rules.map((rule) => rule.text);

  return (
    <section
      className="hx-section hx-decision"
      id="verify"
      data-testid="decision-direction"
      aria-labelledby="decision-title"
    >
      <h2 id="decision-title">{DECISION_TITLE}</h2>
      <p className="hx-section-lead">
        {area}. {preparednessLabel(prep.status)} in regional inventory data.
      </p>
      <div className="hx-decision-grid">
        <article>
          <h3>{DECISION_SHOWS}</h3>
          <ul data-testid="decision-shows">
            {showsParts.map((line) => (
              <li key={line}>{line}</li>
            ))}
          </ul>
        </article>
        <article>
          <h3>{DECISION_MATTERS}</h3>
          <ul data-testid="decision-matters">
            {mattersParts.map((line) => (
              <li key={line}>{line}</li>
            ))}
          </ul>
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
      <p className="hx-note hx-disclaimer-compact">{DECISION_NO_RECOMMENDATION}</p>
    </section>
  );
}
