import { ResultCards } from "./ResultCards";
import type { ResultCardsView } from "./types";

export type ResultColumnProps = {
  view: ResultCardsView;
};

/** Full-width result band. Long Decision 8 tokens stay in the accordion. */
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
