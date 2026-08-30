import { ResultCard } from "./ResultCard";
import type { ResultCardsView } from "./types";

export type ResultCardsProps = {
  view: ResultCardsView;
};

export function ResultCards({ view }: ResultCardsProps) {
  return (
    <section className="result-cards" aria-label="Thermal evidence" data-testid="result-cards">
      <ResultCard card={view.a} />
      <ResultCard card={view.b} />
    </section>
  );
}
