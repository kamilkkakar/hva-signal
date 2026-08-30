import { STRIP_KICKER } from "./copy";
import { PositionAxis } from "./PositionAxis";
import "./charts.css";
import type { HistoricalPositionView } from "./types";

export type HistoricalPositionStripProps = {
  view: HistoricalPositionView;
};

export function HistoricalPositionStrip({ view }: HistoricalPositionStripProps) {
  if (!view.visible) {
    return null;
  }

  return (
    <section
      className="hva-pos-strip"
      data-testid="historical-position-strip"
      data-ordering={view.comparison}
      data-mark-count={view.marks.length}
      aria-label={STRIP_KICKER}
    >
      <p className="kicker">{STRIP_KICKER}</p>
      {view.comparisonStamp && (
        <p
          className="hva-pos-state"
          data-testid="ordering-comparison-state"
          data-ordering={view.comparison}
        >
          {view.comparisonStamp}
        </p>
      )}
      {view.frameCaption && (
        <p className="hva-pos-frame" data-testid="historical-frame-caption">
          {view.frameCaption}
        </p>
      )}
      <PositionAxis
        marks={view.marks}
        selectedZoneId={view.selected?.zoneId ?? null}
        assistive={view.assistive}
      />
      <p className="hva-pos-axis-labels">
        <span data-testid="historical-axis-low">{view.axisLow}</span>
        <span data-testid="historical-axis-high">{view.axisHigh}</span>
      </p>
      <p className="decision-copy">{view.meaning}</p>
    </section>
  );
}
