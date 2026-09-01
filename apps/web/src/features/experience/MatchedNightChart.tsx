import { MATCHED_KEY_FINDING, MATCHED_NOT_CLIMATE, MATCHED_SELECT, MATCHED_TITLE, MATCHED_WINDOW } from "./copy";
import { formatDeltaC, formatTempC } from "./format";
import type { PresentedMatched } from "@/features/judgeShell/decision/types";

type MatchedNightChartProps = {
  view: PresentedMatched;
  areaLabel: string | null;
  analysisAreaCount?: number;
};

function yTicks(min: number, max: number, count = 4): number[] {
  const span = max - min || 1;
  return Array.from({ length: count + 1 }, (_, index) => min + (span * index) / count);
}

export function MatchedNightChart({
  view,
  areaLabel,
  analysisAreaCount = 25,
}: MatchedNightChartProps) {
  const temps = view.years.map((row) => row.meanC);
  const min = temps.length ? Math.min(...temps) - 0.6 : 0;
  const max = temps.length ? Math.max(...temps) + 0.6 : 1;
  const span = max - min || 1;
  const width = 640;
  const height = 240;
  const pad = { l: 48, r: 20, t: 22, b: 36 };
  const plotW = width - pad.l - pad.r;
  const plotH = height - pad.t - pad.b;
  const ticks = yTicks(min, max, 3);
  const points = view.years.map((row, index) => {
    const x = pad.l + (view.years.length === 1 ? plotW / 2 : (index * plotW) / (view.years.length - 1));
    const y = pad.t + plotH - ((row.meanC - min) / span) * plotH;
    return { ...row, x, y };
  });
  const movedWithGeography =
    view.change2024vs2022 != null &&
    view.medianChange != null &&
    Math.abs(view.change2024vs2022 - view.medianChange) <= 0.35;

  return (
    <section
      className="hx-section hx-temporal-card hx-level-1"
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
        <div className="hx-temporal-layout">
          <div className="hx-temporal-chart-pane">
            <p className="hx-chart-summary" data-testid="matched-years">
              {areaLabel ?? "This analysis area"}:{" "}
              {view.years.map((row) => `${row.year} ${formatTempC(row.meanC)}`).join(" · ")}.
            </p>
            <svg
              className="hx-chart hx-chart-large"
              viewBox={`0 0 ${width} ${height}`}
              role="img"
              aria-label={`Matched 03:00 nighttime means for ${areaLabel ?? "the selected analysis area"}`}
              data-testid="matched-night-chart"
              data-viz="line-points"
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
                x={pad.l - 42}
                y={pad.t + plotH / 2}
                textAnchor="middle"
                transform={`rotate(-90 ${pad.l - 42} ${pad.t + plotH / 2})`}
                className="hx-axis-title"
              >
                °C
              </text>
              {points.slice(1).map((point, index) => {
                const prev = points[index];
                if (!prev) return null;
                return (
                  <line
                    key={`${prev.year}-${point.year}`}
                    x1={prev.x}
                    y1={prev.y}
                    x2={point.x}
                    y2={point.y}
                    className="hx-trend-line"
                  />
                );
              })}
              {points.map((point) => (
                <g key={point.year}>
                  <circle cx={point.x} cy={point.y} r="6" className="hx-dot" data-testid={`matched-dot-${point.year}`} />
                  <text x={point.x} y={point.y - 12} textAnchor="middle" className="hx-chart-value">
                    {formatTempC(point.meanC)}
                  </text>
                  <text x={point.x} y={height - 10} textAnchor="middle" className="hx-chart-label">
                    {point.year}
                  </text>
                </g>
              ))}
            </svg>
          </div>
          <aside className="hx-temporal-interpret" data-testid="matched-interpretation">
            <p className="hx-kicker">{MATCHED_KEY_FINDING}</p>
            <p data-testid="matched-change">
              2024 {formatTempC(view.years[view.years.length - 1]?.meanC ?? 0)}
              {" · "}
              {formatDeltaC(view.change2024vs2022 ?? 0)} vs 2022
            </p>
            <p data-testid="matched-finding">
              {(view.change2024vs2022 ?? 0) >= 0 ? "Higher" : "Lower"} by{" "}
              {Math.abs(view.change2024vs2022 ?? 0).toFixed(2)} °C than the 2022 matched window.
            </p>
            <p data-testid="matched-median">
              Geography median: {formatDeltaC(view.medianChange ?? 0)} ({analysisAreaCount} areas).
            </p>
            <p data-testid="matched-nights">
              {view.nightsTotal} matched nights
              {view.nightsWarmer != null ? ` · ${view.nightsWarmer} warmer in 2024` : ""}.
            </p>
            {movedWithGeography ? (
              <p data-testid="matched-geo-read">Moved with the wider geography.</p>
            ) : null}
            <details className="hx-method">
              <summary>About this comparison</summary>
              <p>{MATCHED_WINDOW}</p>
              <p className="hx-note">{MATCHED_NOT_CLIMATE}</p>
            </details>
          </aside>
        </div>
      )}
    </section>
  );
}
