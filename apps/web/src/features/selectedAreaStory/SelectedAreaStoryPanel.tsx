import { MAP_MODE_LABEL } from "@/features/areaContext/copy";
import type { MapMode } from "@/features/areaContext/types";
import { GEOID_DETAILS_SUMMARY } from "./copy";
import type { SelectedAreaDecisionStory } from "./types";
import "./selectedAreaStory.css";

export type SelectedAreaStoryPanelProps = {
  story: SelectedAreaDecisionStory;
  mode?: MapMode;
};

const MAX_VISIBLE_FACTS = 6;

export function SelectedAreaStoryPanel({
  story,
  mode = "THERMAL",
}: SelectedAreaStoryPanelProps) {
  const thermal = story.questions.thermal;
  const facts = story.questions.different.facts.slice(0, MAX_VISIBLE_FACTS);
  const modeMeta = story.mapModes.find((row) => row.mode === mode) ?? story.mapModes[0];
  const contextMode = mode !== "THERMAL";
  return (
    <article
      className="selected-area-story"
      data-testid="selected-area-story"
      data-thermal={thermal.status}
      data-area-number={story.identity.areaNumber ?? "missing"}
      aria-label={story.identity.label ?? "Selected analysis area"}
    >
      <p className="kicker">{story.identity.label ?? "Unknown analysis area"}</p>
      <details data-testid="selected-area-geoid">
        <summary>{GEOID_DETAILS_SUMMARY}</summary>
        <p>{story.identity.geoid ?? "Census tract is not available"}</p>
      </details>

      <section data-source="fortyguard" data-testid="story-thermal">
        <h3>{thermal.label}</h3>
        {thermal.a.hasRealPane && thermal.a.orderShown ? (
          <>
            <p data-testid="story-thermal-a">
              This analysis area has a historical position. The thermal order is shown.
            </p>
            <details data-testid="story-thermal-a-method">
              <summary>Method notes</summary>
              <p>
                {thermal.a.q_A != null ? `q_A ${thermal.a.q_A.toFixed(3)}` : "q_A not published"}
                {thermal.a.decision8 ? `. Decision 8 ${thermal.a.decision8}` : "."}
              </p>
            </details>
          </>
        ) : thermal.a.kind === "order_withheld" ? (
          <p data-testid="story-thermal-a">
            Historical position is available. The thermal order is withheld.
          </p>
        ) : (
          <p data-testid="story-thermal-a">Historical-position evidence is not available for this analysis area.</p>
        )}
        {thermal.b.kind === "cached" && thermal.b.temperatureC != null ? (
          <p data-testid="story-thermal-b">
            {thermal.b.wording}: {thermal.b.temperatureC.toFixed(1)} °C · {thermal.b.coverage} ·{" "}
            {thermal.b.clock} {thermal.b.timezone}
          </p>
        ) : (
          <p data-testid="story-thermal-b">
            Cached nighttime temperature is not available for this analysis area.
          </p>
        )}
      </section>

      <section data-source="acs-canopy" data-testid="story-different">
        <h3>{story.questions.different.label}</h3>
        <ul data-testid="story-facts">
          {facts.map((fact) => (
            <li key={fact.kind} data-source={fact.sourceFamily} data-comparison={String(fact.comparisonAllowed)}>
              {fact.sentence}
            </li>
          ))}
        </ul>
      </section>

      <section data-source="mag" data-testid="story-support">
        <h3>{story.questions.support.label}</h3>
        {story.questions.support.sentences.map((line) => (
          <p key={line}>{line}</p>
        ))}
        <p>{story.questions.support.disclaimer}</p>
      </section>

      <section data-testid="story-verify">
        <h3>{story.questions.verify.label}</h3>
        <ol>
          {story.questions.verify.rules.map((rule) => (
            <li key={rule.id} data-rule={rule.id}>
              {rule.text}
            </li>
          ))}
        </ol>
      </section>

      {modeMeta ? (
        <p
          className="story-map-mode"
          data-testid="story-map-mode"
          data-source-family={contextMode ? "context" : "fortyguard"}
        >
          {MAP_MODE_LABEL[modeMeta.mode]} · {modeMeta.source} · {modeMeta.year} · {modeMeta.unit}. {modeMeta.meaning}
        </p>
      ) : null}
    </article>
  );
}
