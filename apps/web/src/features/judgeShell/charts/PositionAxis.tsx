import type { HistoricalPositionMark } from "./types";

export type PositionAxisProps = {
  marks: readonly HistoricalPositionMark[];
  selectedZoneId: string | null;
  assistive: string;
  testId?: string;
};

const TRACK_LEFT = 2;
const TRACK_WIDTH = 96;
const TRACK_Y = 9;

function markX(position: number): number {
  return TRACK_LEFT + position * TRACK_WIDTH;
}

export function PositionAxis({
  marks,
  selectedZoneId,
  assistive,
  testId = "historical-position-axis",
}: PositionAxisProps) {
  return (
    <svg
      className="hva-pos-axis"
      viewBox="0 0 100 18"
      role="img"
      aria-label={assistive}
      data-testid={testId}
      data-decorative="false"
      data-mark-count={marks.length}
    >
      <line
        className="hva-pos-track"
        x1={TRACK_LEFT}
        y1={TRACK_Y}
        x2={TRACK_LEFT + TRACK_WIDTH}
        y2={TRACK_Y}
      />
      {marks.map((mark) => {
        const selected = selectedZoneId === mark.zoneId;
        return (
          <circle
            key={mark.zoneId}
            className={selected ? "hva-pos-mark-selected" : "hva-pos-mark"}
            cx={markX(mark.position)}
            cy={TRACK_Y}
            r={selected ? 2.6 : 1.35}
            data-testid={selected ? "historical-position-selected-mark" : "historical-position-mark"}
            data-zone={mark.zoneId}
            data-position={mark.position}
          />
        );
      })}
    </svg>
  );
}
