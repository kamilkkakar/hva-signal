import { MATCHED_NOT_CLIMATE, MATCHED_SELECT, MATCHED_TITLE, MATCHED_WINDOW } from "./copy";
import { formatDeltaC, formatTempC } from "./format";
import type { PresentedMatched } from "@/features/judgeShell/decision/types";

type MatchedNightChartProps = {
  view: PresentedMatched;
  areaLabel: string | null;
};

export function MatchedNightChart({ view, areaLabel }: MatchedNightChartProps) {
  const temps = view.years.map((row) => row.meanC);
  const min = temps.length ? Math.min(...temps) - 0.4 : 0;
  const max = temps.length ? Math.max(...temps) + 0.4 : 1;
  const span = max - min || 1;
  const width = 560;
  const height = 180;
  const pad = { l: 44, r: 16, t: 16, b: 36 };
  const plotW = width - pad.l - pad.r;
  const plotH = height - pad.t - pad.b;
  const barW = plotW / 5;

  return (
    <section className="hx-section" data-testid="matched-nighttime" aria-labelledby="matched-night-title">
      <p className="hx-kicker">Matched nighttime</p>
      <h2 id="matched-night-title">{MATCHED_TITLE}</h2>
      <p className="hx-section-lead">{MATCHED_WINDOW}</p>
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
            {view.nightsTotal}.
          </p>
          <svg
            className="hx-chart"
            viewBox={`0 0 ${width} ${height}`}
            role="img"
            aria-label={`Matched 03:00 nighttime means for ${areaLabel ?? "the selected analysis area"}`}
            data-testid="matched-night-chart"
            data-autostretch="false"
          >
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
          </svg>
          <p data-testid="matched-change">2024 vs 2022: {formatDeltaC(view.change2024vs2022 ?? 0)}</p>
          <p data-testid="matched-median">25-area median: {formatDeltaC(view.medianChange ?? 0)}</p>
          <p data-testid="matched-nights">
            Matched nights warmer: {view.nightsWarmer} / {view.nightsTotal}
          </p>
          <p className="hx-note">{MATCHED_NOT_CLIMATE}</p>
        </>
      )}
    </section>
  );
}
