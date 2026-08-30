import {
  DOES_NOT_LABEL,
  STORY_ARIA,
  STORY_KICKER,
  SUPPORTS_LABEL,
} from "./copy";
import { HowDetermined } from "./HowDetermined";
import "./resultStory.css";
import type { ResultStoryView } from "./types";

export type ResultStoryProps = {
  view: ResultStoryView;
};

export function ResultStory({ view }: ResultStoryProps) {
  return (
    <article
      className="result-story"
      data-testid="result-story"
      data-story-kind={view.kind}
      aria-label={STORY_ARIA}
    >
      <p className="kicker">{STORY_KICKER}</p>
      <p
        className="result-story-stamp"
        data-testid="result-story-stamp"
        data-story-kind={view.kind}
      >
        {view.stamp}
      </p>
      <h2 className="result-story-headline" data-testid="result-story-headline">
        {view.headline}
      </h2>
      <p className="result-story-summary" data-testid="result-story-summary">
        {view.summary}
      </p>
      <dl className="result-story-context" data-testid="result-story-context">
        {view.context.map((item) => (
          <div key={item.label} className="result-story-context-item">
            <dt>{item.label}</dt>
            <dd>{item.value}</dd>
          </div>
        ))}
      </dl>
      <dl className="result-story-supports-grid">
        <div>
          <dt>{SUPPORTS_LABEL}</dt>
          <dd data-testid="result-story-supports">{view.supports}</dd>
        </div>
        <div>
          <dt>{DOES_NOT_LABEL}</dt>
          <dd data-testid="result-story-does-not">{view.doesNotEstablish}</dd>
        </div>
      </dl>
      <HowDetermined how={view.how} />
    </article>
  );
}
