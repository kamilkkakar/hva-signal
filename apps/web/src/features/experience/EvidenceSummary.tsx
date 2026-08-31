import type { ReactNode } from "react";
import {
  RANKING_SUPPORTED_BODY,
  RANKING_SUPPORTED_TITLE,
  RANKING_WITHHELD_BODY,
  RANKING_WITHHELD_NEXT,
  RANKING_WITHHELD_TITLE,
} from "./copy";

type EvidenceSummaryProps = {
  withheld: boolean;
  ready: boolean;
  children?: ReactNode;
};

export function EvidenceSummary({ withheld, ready, children }: EvidenceSummaryProps) {
  if (!ready) {
    return (
      <section className="hx-summary hx-summary-loading" data-testid="evidence-summary" aria-busy>
        <p className="hx-kicker">Historical comparison</p>
        <p>The 25 analysis areas are on the map. Historical ranking appears after this night is analyzed.</p>
        {children}
      </section>
    );
  }
  return (
    <section
      className="hx-summary"
      data-testid="evidence-summary"
      data-ranking={withheld ? "withheld" : "supported"}
    >
      <p className="hx-kicker">{withheld ? RANKING_WITHHELD_TITLE : RANKING_SUPPORTED_TITLE}</p>
      <p data-testid="ranking-interpretation">
        {withheld ? RANKING_WITHHELD_BODY : RANKING_SUPPORTED_BODY}
      </p>
      {withheld ? (
        <p data-testid="ranking-next" className="hx-note">
          {RANKING_WITHHELD_NEXT}
        </p>
      ) : null}
      {children}
    </section>
  );
}
