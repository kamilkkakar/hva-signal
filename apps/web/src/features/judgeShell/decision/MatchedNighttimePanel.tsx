import {
  MATCHED_DISCLOSURE,
  MATCHED_NOT_CLIMATE,
  MATCHED_TITLE,
} from "./copy";
import { formatDeltaC, formatTempC } from "./present";
import { StoryCard } from "./StoryCard";
import type { PresentedMatched } from "./types";

type MatchedNighttimePanelProps = {
  view: PresentedMatched;
};

export function MatchedNighttimePanel({ view }: MatchedNighttimePanelProps) {
  return (
    <StoryCard title={MATCHED_TITLE} status={view.status} testId="matched-nighttime">
      {view.status !== "AVAILABLE" ? (
        <p className="decision-missing">{view.reason}</p>
      ) : (
        <>
          <ul className="decision-years" data-testid="matched-years">
            {view.years.map((row) => (
              <li key={row.year}>
                <span>{row.year}</span>
                <strong>{formatTempC(row.meanC)}</strong>
              </li>
            ))}
          </ul>
          <p data-testid="matched-change">
            2024 vs 2022: {formatDeltaC(view.change2024vs2022 ?? 0)}
          </p>
          <p data-testid="matched-median">
            25-area median: {formatDeltaC(view.medianChange ?? 0)}
          </p>
          <p data-testid="matched-nights">
            Matched nights warmer: {view.nightsWarmer} / {view.nightsTotal}
          </p>
          <p className="decision-disclosure">{MATCHED_DISCLOSURE}</p>
          <p className="decision-disclosure">{MATCHED_NOT_CLIMATE}</p>
        </>
      )}
    </StoryCard>
  );
}
