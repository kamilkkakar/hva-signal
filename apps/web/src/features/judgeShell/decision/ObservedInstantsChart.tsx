import { INSTANTS_DIFF_LABEL, INSTANTS_GAP, INSTANTS_SUBTITLE, INSTANTS_TITLE } from "./copy";
import { formatDeltaC, formatTempC } from "./present";
import { StoryCard } from "./StoryCard";
import type { PresentedSequence } from "./types";

type ObservedInstantsChartProps = {
  view: PresentedSequence;
};

export function ObservedInstantsChart({ view }: ObservedInstantsChartProps) {
  const temps = view.instants.map((item) => item.temperatureC);
  const min = temps.length ? Math.min(...temps) - 1 : 0;
  const max = temps.length ? Math.max(...temps) + 1 : 1;
  const span = max - min || 1;
  const width = 560;
  const height = 160;
  const pad = 28;
  const points = view.instants.map((item, index) => {
    const x = pad + (index * (width - pad * 2)) / 3;
    const y = height - pad - ((item.temperatureC - min) / span) * (height - pad * 2);
    return { ...item, x, y };
  });
  return (
    <StoryCard title={INSTANTS_TITLE} status={view.status} testId="observed-instants">
      <p className="decision-disclosure">{INSTANTS_SUBTITLE}</p>
      {view.status !== "AVAILABLE" ? (
        <p className="decision-missing">{view.reason}</p>
      ) : (
        <>
          <svg
            className="decision-instants-svg"
            viewBox={`0 0 ${width} ${height}`}
            role="img"
            aria-label="Four discrete observed thermal markers"
            data-testid="observed-instants-chart"
            data-autostretch="false"
          >
            {points.slice(1).map((point, index) => {
              const prev = points[index];
              return (
                <g key={`${prev.instantId}-${point.instantId}`}>
                  <line
                    x1={prev.x}
                    y1={prev.y}
                    x2={point.x}
                    y2={point.y}
                    stroke="currentColor"
                    strokeDasharray="4 6"
                    strokeWidth="1.5"
                    opacity="0.45"
                  />
                  <text
                    x={(prev.x + point.x) / 2}
                    y={(prev.y + point.y) / 2 - 8}
                    textAnchor="middle"
                    className="decision-gap"
                  >
                    {INSTANTS_GAP}
                  </text>
                </g>
              );
            })}
            {points.map((point) => (
              <g key={point.instantId}>
                <circle cx={point.x} cy={point.y} r="5" fill="currentColor" />
                <text x={point.x} y={point.y - 12} textAnchor="middle">
                  {formatTempC(point.temperatureC)}
                </text>
                <text x={point.x} y={height - 6} textAnchor="middle">
                  {point.label}
                </text>
              </g>
            ))}
          </svg>
          <ul className="decision-instant-list" data-testid="observed-instant-list">
            {view.instants.map((item) => (
              <li key={item.instantId} data-instant={item.instantId} data-qa="no">
                <span>{item.label}</span>
                <strong>{formatTempC(item.temperatureC)}</strong>
              </li>
            ))}
          </ul>
          <ul className="decision-diffs" data-testid="observed-diffs">
            {view.differences.map((item) => (
              <li key={`${item.fromId}-${item.toId}`}>
                {INSTANTS_DIFF_LABEL}: {formatDeltaC(item.deltaC)}
              </li>
            ))}
          </ul>
        </>
      )}
    </StoryCard>
  );
}
