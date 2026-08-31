import { MATCHED_NOT_CLIMATE, MATCHED_SELECT, MATCHED_TITLE, MATCHED_WINDOW } from "./copy";
import { formatDeltaC, formatTempC } from "./format";
import type { PresentedMatched } from "@/features/judgeShell/decision/types";

type MatchedNightChartProps = {
  view: PresentedMatched;
  areaLabel: string | null;
};

function yTicks(min: number, max: number, count = 4): number[] {
  const span = max - min || 1;
  return Array.from({ length: count + 1 }, (_, index) => min + (span * index) / count);
}

export function MatchedNightChart({ view, areaLabel }: MatchedNightChartProps) {
  const temps = view.years.map((row) => row.meanC);
  const min = temps.length ? Math.min(...temps) - 0.6 : 0;
  const max = temps.length ? Math.max(...temps) + 0.6 : 1;
  const span = max - min || 1;
  const width = 560;
  const height = 220;
  const pad = { l: 52, r: 16, t: 16, b: 40 };
  const plotW = width - pad.l - pad.r;
  const plotH = height - pad.t - pad.b;
  const barW = plotW / 5;
  const ticks = yTicks(min, max);

  return (
    <section
      className="hx-section"
      id="changed"
      data-testid="matched-nighttime"
      aria-labelledby="matched-night-title"
    >
      <h2 id="matched-night-title">{MATCHED_TITLE}</h2>
      {view.status !== "AVAILABLE" ? (
        <p className="hx-missing" data-testid="matched-missing">
          {view.reason ?? MATCHED_SELECT}
        </p>
      ) : (
        <>
          <p className="hx-chart-summary" data-testid="matched-years">
            {areaLabel ?? "This analysis area"}:{" "}
            {view.years.map((row) => `${row.year} ${formatTempC(row.meanC)}`).join(" · ")}
            . 2024 vs 2022: {formatDeltaC(view.change2024vs2022 ?? 0)}. 25-area median:{" "}
            {formatDeltaC(view.medianChange ?? 0)}. Matched nights warmer: {view.nightsWarmer} /{" "}
            {view.nightsTotal} ({view.nightsTotal} matched 03:00 nights).
          </p>
          <svg
            className="hx-chart"
            viewBox={`0 0 ${width} ${height}`}
            role="img"
            aria-label={`Matched 03:00 nighttime means for ${areaLabel ?? "the selected analysis area"}`}
            data-testid="matched-night-chart"
            data-autostretch="false"
          >
            <line
              x1={pad.l}
              y1={pad.t}
              x2={pad.l}
              y2={pad.t + plotH}
              className="hx-axis-line"
            />
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
            {view.years.map((row, index) => {
              const x = pad.l + index * (plotW / 3) + (plotW / 3 - barW) / 2;
              const h = ((row.meanC - min) / span) * plotH;
              const y = pad.t + plotH - h;
              return (
                <g key={row.year}>
                  <rect x={x} y={y} width={barW} height={h} className="hx-bar" />
                  <text x={x + barW / 2} y={y - 6} textAnchor="middle" className="hx-chart-value">
                    {formatTempC(row.meanC)}
                  </text>
                  <text x={x + barW / 2} y={height - 10} textAnchor="middle" className="hx-chart-label">
                    {row.year}
                  </text>
                </g>
              );
            })}
            <line
              x1={pad.l}
              y1={pad.t + plotH - ((view.years[0]?.meanC ?? min) - min) / span * plotH}
              x2={pad.l + plotW}
              y2={pad.t + plotH - ((view.years[0]?.meanC ?? min) - min) / span * plotH}
              className="hx-baseline-line"
              strokeDasharray="4 4"
            />
          </svg>
          <p data-testid="matched-change">2024 vs 2022: {formatDeltaC(view.change2024vs2022 ?? 0)}</p>
          <p data-testid="matched-median">25-area median change: {formatDeltaC(view.medianChange ?? 0)}</p>
          <p data-testid="matched-nights">
            Matched nights warmer: {view.nightsWarmer} / {view.nightsTotal}
          </p>
          <details className="hx-method">
            <summary>About this comparison</summary>
            <p>{MATCHED_WINDOW}</p>
            <p className="hx-note">{MATCHED_NOT_CLIMATE}</p>
          </details>
        </>
      )}
    </section>
  );
}
