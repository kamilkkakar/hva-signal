import { ResultCards } from "./ResultCards";
import type { ResultCardsView } from "./types";

export type ResultColumnProps = {
  view: ResultCardsView;
};

/** 300px-safe third column. Long Decision 8 tokens stay out of this rail. */
export function ResultColumn({ view }: ResultColumnProps) {
  return (
    <aside
      className="result-column"
      data-testid="result-column"
      aria-label="Decision panel"
    >
      <ResultCards view={view} />
    </aside>
  );
}
