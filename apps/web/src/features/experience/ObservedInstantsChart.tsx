import { INSTANTS_GAP, INSTANTS_SELECT, INSTANTS_SUBTITLE, INSTANTS_TITLE } from "./copy";
import { formatDeltaC, formatTempC } from "./format";
import type { PresentedSequence } from "@/features/judgeShell/decision/types";

type ObservedInstantsChartProps = {
  view: PresentedSequence;
  areaLabel: string | null;
};

export function ObservedInstantsChart({ view, areaLabel }: ObservedInstantsChartProps) {
  const temps = view.instants.map((item) => item.temperatureC);
  const min = temps.length ? Math.min(...temps) - 1 : 0;
  const max = temps.length ? Math.max(...temps) + 1 : 1;
  const span = max - min || 1;
  const width = 560;
  const height = 180;
  const pad = 36;
  const points = view.instants.map((item, index) => {
    const x = pad + (index * (width - pad * 2)) / 3;
    const y = height - pad - ((item.temperatureC - min) / span) * (height - pad * 2);
    return { ...item, x, y };
  });

  return (
    <section className="hx-section" data-testid="observed-instants" aria-labelledby="observed-instants-title">
      <p className="hx-kicker">Observed instants</p>
      <h2 id="observed-instants-title">{INSTANTS_TITLE}</h2>
      <p className="hx-section-lead">{INSTANTS_SUBTITLE}</p>
      {view.status !== "AVAILABLE" ? (
        <p className="hx-missing">{view.reason ?? INSTANTS_SELECT}</p>
      ) : (
        <>
          <p className="hx-chart-summary" data-testid="observed-instant-list">
            {areaLabel ?? "This analysis area"}:{" "}
            {view.instants
              .map((item) => `${item.label} ${formatTempC(item.temperatureC)}`)
              .join(" · ")}
            . Connecting guides mark unobserved intervals.
          </p>
          <svg
            className="hx-chart"
            viewBox={`0 0 ${width} ${height}`}
            role="img"
            aria-label="Four discrete observed thermal markers with unobserved intervals"
            data-testid="observed-instants-chart"
            data-autostretch="false"
          >
            {points.slice(1).map((point, index) => {
              const prev = points[index];
              if (prev == null) {
                return null;
              }
              return (
                <g key={`${prev.instantId}-${point.instantId}`}>
                  <line
                    x1={prev.x}
                    y1={prev.y}
                    x2={point.x}
                    y2={point.y}
                    className="hx-gap-line"
                  />
                  <text
                    x={(prev.x + point.x) / 2}
                    y={(prev.y + point.y) / 2 - 10}
                    textAnchor="middle"
                    className="hx-gap-label"
                  >
                    {INSTANTS_GAP}
                  </text>
                </g>
              );
            })}
            {points.map((point) => (
              <g key={point.instantId}>
                <circle cx={point.x} cy={point.y} r="6" className="hx-dot" />
                <text x={point.x} y={point.y - 14} textAnchor="middle" className="hx-chart-value">
                  {formatTempC(point.temperatureC)}
                </text>
                <text x={point.x} y={height - 8} textAnchor="middle" className="hx-chart-label">
                  {point.label}
                </text>
              </g>
            ))}
          </svg>
          <ul className="hx-diffs" data-testid="observed-diffs">
            {view.differences.map((item) => (
              <li key={`${item.fromId}-${item.toId}`}>
                {item.fromId} → {item.toId}: {formatDeltaC(item.deltaC)}
              </li>
            ))}
          </ul>
        </>
      )}
    </section>
  );
}
