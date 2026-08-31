import { INSTANTS_GAP, INSTANTS_SELECT, INSTANTS_SUBTITLE, INSTANTS_TITLE } from "./copy";
import { formatDeltaC, formatTempC } from "./format";
import type { PresentedSequence } from "@/features/judgeShell/decision/types";

type ObservedInstantsChartProps = {
  view: PresentedSequence;
  areaLabel: string | null;
};

function yTicks(min: number, max: number, count = 4): number[] {
  const span = max - min || 1;
  return Array.from({ length: count + 1 }, (_, index) => min + (span * index) / count);
}

export function ObservedInstantsChart({ view, areaLabel }: ObservedInstantsChartProps) {
  const temps = view.instants.map((item) => item.temperatureC);
  const min = temps.length ? Math.min(...temps) - 1 : 0;
  const max = temps.length ? Math.max(...temps) + 1 : 1;
  const span = max - min || 1;
  const width = 560;
  const height = 220;
  const pad = { l: 52, r: 36, t: 16, b: 40 };
  const plotW = width - pad.l - pad.r;
  const plotH = height - pad.t - pad.b;
  const ticks = yTicks(min, max);
  const points = view.instants.map((item, index) => {
    const x = pad.l + (index * plotW) / 3;
    const y = pad.t + plotH - ((item.temperatureC - min) / span) * plotH;
    return { ...item, x, y };
  });

  return (
    <section
      className="hx-section"
      id="observed"
      data-testid="observed-instants"
      aria-labelledby="observed-instants-title"
    >
      <h2 id="observed-instants-title">{INSTANTS_TITLE}</h2>
      {view.status !== "AVAILABLE" ? (
        <p className="hx-missing">{view.reason ?? INSTANTS_SELECT}</p>
      ) : (
        <>
          <p className="hx-chart-summary" data-testid="observed-instant-list">
            {areaLabel ?? "This analysis area"}:{" "}
            {view.instants
              .map((item) => `${item.label} ${formatTempC(item.temperatureC)}`)
              .join(" · ")}
            . Dashed guides mark unobserved intervals only — not a continuous curve.
          </p>
          <svg
            className="hx-chart"
            viewBox={`0 0 ${width} ${height}`}
            role="img"
            aria-label="Four discrete observed thermal markers with unobserved intervals"
            data-testid="observed-instants-chart"
            data-autostretch="false"
          >
            <line x1={pad.l} y1={pad.t} x2={pad.l} y2={pad.t + plotH} className="hx-axis-line" />
            <line
              x1={pad.l}
              y1={pad.t + plotH}
              x2={pad.l + plotW}
              y2={pad.t + plotH}
              className="hx-axis-line"
            />
            {ticks.map((tick) => {
              const y = pad.t + plotH - ((tick - min) / span) * plotH;
              return (
                <g key={tick}>
                  <line x1={pad.l - 4} y1={y} x2={pad.l} y2={y} className="hx-axis-tick" />
                  <text x={pad.l - 8} y={y + 4} textAnchor="end" className="hx-axis-label">
                    {formatTempC(tick)}
                  </text>
                </g>
              );
            })}
            <text
              x={pad.l - 38}
              y={pad.t + plotH / 2}
              textAnchor="middle"
              transform={`rotate(-90 ${pad.l - 38} ${pad.t + plotH / 2})`}
              className="hx-axis-title"
            >
              °C
            </text>
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
                <circle cx={point.x} cy={point.y} r="7" className="hx-dot" />
                <text x={point.x} y={point.y - 16} textAnchor="middle" className="hx-chart-value">
                  {formatTempC(point.temperatureC)}
                </text>
                <text x={point.x} y={height - 10} textAnchor="middle" className="hx-chart-label">
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
          <details className="hx-method">
            <summary>About these observations</summary>
            <p>{INSTANTS_SUBTITLE}</p>
          </details>
        </>
      )}
    </section>
  );
}
