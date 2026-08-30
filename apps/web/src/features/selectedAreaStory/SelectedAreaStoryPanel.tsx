import { MAP_MODE_LABEL } from "@/features/areaContext/copy";
import type { MapMode } from "@/features/areaContext/types";
import type { SelectedAreaDecisionStory } from "./types";
import "./selectedAreaStory.css";

export type SelectedAreaStoryPanelProps = {
  story: SelectedAreaDecisionStory;
  mode?: MapMode;
};

export function SelectedAreaStoryPanel({
  story,
  mode = "THERMAL",
}: SelectedAreaStoryPanelProps) {
  const thermal = story.questions.thermal;
  const modeMeta = story.mapModes.find((row) => row.mode === mode) ?? story.mapModes[0];
  return (
    <article
      className="selected-area-story"
      data-testid="selected-area-story"
      data-thermal={thermal.status}
      data-area-number={story.identity.areaNumber ?? "missing"}
      aria-label={story.identity.label ?? "Selected analysis area"}
    >
      <p className="kicker">{story.identity.label ?? "Unknown analysis area"}</p>
      <p data-testid="selected-area-geoid">{story.identity.geoid ?? "no GEOID"}</p>

      <section data-source="fortyguard" data-testid="story-thermal">
        <h3>{thermal.label}</h3>
        <p data-testid="story-thermal-status">THERMAL={thermal.status}</p>
        {thermal.a.hasRealPane ? (
          <p data-testid="story-thermal-a">
            Signal A: {thermal.a.kind}
            {thermal.a.orderShown && thermal.a.q_A != null ? ` · q_A ${thermal.a.q_A.toFixed(3)}` : ""}
            {thermal.a.decision8 ? ` · Decision 8 ${thermal.a.decision8}` : ""}
          </p>
        ) : (
          <p data-testid="story-thermal-a">Signal A pane is not available for this analysis area.</p>
        )}
        {thermal.b.kind === "cached" && thermal.b.temperatureC != null ? (
          <p data-testid="story-thermal-b">
            {thermal.b.wording}: {thermal.b.temperatureC.toFixed(1)} °C · {thermal.b.coverage} ·{" "}
            {thermal.b.clock} {thermal.b.timezone}
          </p>
        ) : (
          <p data-testid="story-thermal-b">Cached nighttime temperature is not available for this GEOID.</p>
        )}
      </section>

      <section data-source="acs-canopy" data-testid="story-different">
        <h3>{story.questions.different.label}</h3>
        <ul>
          {story.questions.different.facts.map((fact) => (
            <li key={fact.kind} data-source={fact.sourceFamily} data-comparison={String(fact.comparisonAllowed)}>
              {fact.sentence}
            </li>
          ))}
        </ul>
      </section>

      <section data-source="mag" data-testid="story-support">
        <h3>{story.questions.support.label}</h3>
        <p data-testid="story-preparedness-status">{story.questions.support.status}</p>
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
        <p className="story-map-mode" data-testid="story-map-mode">
          {MAP_MODE_LABEL[modeMeta.mode]} · {modeMeta.source} · {modeMeta.year} · {modeMeta.unit}. {modeMeta.meaning}
        </p>
      ) : null}
    </article>
  );
}
