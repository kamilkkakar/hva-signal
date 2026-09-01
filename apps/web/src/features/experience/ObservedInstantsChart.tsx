import { INSTANTS_DIFF_LABEL, INSTANTS_GAP, INSTANTS_HIGH_LABEL, INSTANTS_SELECT, INSTANTS_SUBTITLE, INSTANTS_TITLE } from "./copy";
import { formatDeltaC, formatTempC } from "./format";
import { deriveThermalFindings } from "./derivedFindings";
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
  const findings = deriveThermalFindings(
    view.instants.map((item) => ({
      id: item.instantId,
      label: item.label,
      temperatureC: item.temperatureC,
    })),
  );

  if (view.status === "AVAILABLE" && findings.count < 2) {
    return (
      <section
        className="hx-section hx-temporal-card hx-level-1"
        id="observed"
        data-testid="observed-instants"
        aria-labelledby="observed-instants-title"
      >
        <h2 id="observed-instants-title">{INSTANTS_TITLE}</h2>
        <p className="hx-note" data-testid="observed-single-instant">
          {areaLabel ?? "This analysis area"}:{" "}
          {findings.highest
            ? `${findings.highest.label} ${formatTempC(findings.highest.temperatureC)}`
            : "one published observation"}
          . Additional timestamps are required before pairwise gaps are shown.
        </p>
      </section>
    );
  }

  const temps = view.instants.map((item) => item.temperatureC);
  const min = temps.length ? Math.min(...temps) - 1 : 0;
  const max = temps.length ? Math.max(...temps) + 1 : 1;
  const span = max - min || 1;
  const width = 680;
  const height = 250;
  const pad = { l: 98, r: 34, t: 28, b: 50 };
  const plotW = width - pad.l - pad.r;
  const plotH = height - pad.t - pad.b;
  const pointInset = 34;
  const pointSpan = Math.max(0, plotW - pointInset * 2);
  const ticks = yTicks(min, max, 3);
  const points = view.instants.map((item, index) => {
    const x =
      view.instants.length === 1
        ? pad.l + plotW / 2
        : pad.l + pointInset + (index * pointSpan) / Math.max(view.instants.length - 1, 1);
    const y = pad.t + plotH - ((item.temperatureC - min) / span) * plotH;
    return { ...item, x, y };
  });
  const high = findings.highest;

  return (
    <section
      className="hx-section hx-temporal-card hx-level-1"
      id="observed"
      data-testid="observed-instants"
      aria-labelledby="observed-instants-title"
    >
      <h2 id="observed-instants-title">{INSTANTS_TITLE}</h2>
      {view.status !== "AVAILABLE" ? (
        <p className="hx-missing">{view.reason ?? INSTANTS_SELECT}</p>
      ) : (
        <div className="hx-temporal-layout">
          <div className="hx-temporal-chart-pane">
            <p className="hx-chart-summary" data-testid="observed-instant-list">
              {areaLabel ?? "This analysis area"}:{" "}
              {view.instants
                .map((item) => `${item.label} ${formatTempC(item.temperatureC)}`)
                .join(" · ")}
              .
            </p>
            <svg
              className="hx-chart hx-chart-large"
              viewBox={`0 0 ${width} ${height}`}
              role="img"
              aria-label="Observed thermal markers with unobserved intervals"
              data-testid="observed-instants-chart"
              data-autostretch="false"
            >
              <line
                x1={pad.l}
                y1={pad.t}
                x2={pad.l}
                y2={pad.t + plotH}
                className="hx-axis-line"
                data-testid="observed-y-axis"
              />
              <line
                x1={pad.l}
                y1={pad.t + plotH}
                x2={pad.l + plotW}
                y2={pad.t + plotH}
                className="hx-axis-line"
                data-testid="observed-x-axis"
              />
              {ticks.map((tick) => {
                const y = pad.t + plotH - ((tick - min) / span) * plotH;
                return (
                  <g key={tick}>
                    <line x1={pad.l - 6} y1={y} x2={pad.l} y2={y} className="hx-axis-tick" />
                    <text x={pad.l - 16} y={y + 4} textAnchor="end" className="hx-axis-label">
                      {formatTempC(tick)}
                    </text>
                  </g>
                );
              })}
              <text
                x={22}
                y={pad.t + plotH / 2}
                textAnchor="middle"
                transform={`rotate(-90 22 ${pad.t + plotH / 2})`}
                className="hx-axis-title"
              >
                Temperature (°C)
              </text>
              {points.slice(1).map((point, index) => {
                const prev = points[index];
                if (prev == null) return null;
                return (
                  <line
                    key={`${prev.instantId}-${point.instantId}`}
                    x1={prev.x}
                    y1={prev.y}
                    x2={point.x}
                    y2={point.y}
                    className="hx-gap-line"
                  />
                );
              })}
              {points.map((point) => (
                <g key={point.instantId}>
                  <circle
                    cx={point.x}
                    cy={point.y}
                    r={high?.id === point.instantId ? 6 : 5}
                    className={high?.id === point.instantId ? "hx-dot hx-dot-high" : "hx-dot"}
                  />
                  <text x={point.x} y={Math.max(pad.t + 10, point.y - 12)} textAnchor="middle" className="hx-chart-value">
                    {formatTempC(point.temperatureC)}
                  </text>
                  <text x={point.x} y={height - 14} textAnchor="middle" className="hx-chart-label">
                    {point.label}
                  </text>
                </g>
              ))}
            </svg>
          </div>
          <aside className="hx-temporal-interpret">
            {high ? (
              <p className="hx-observed-high" data-testid="observed-high">
                <span className="hx-kicker">{INSTANTS_HIGH_LABEL}</span>
                <strong>
                  {high.label} · {formatTempC(high.temperatureC)}
                </strong>
              </p>
            ) : null}
            {findings.spanC != null ? (
              <p className="hx-note" data-testid="observed-span">
                Overall span {Math.abs(findings.spanC).toFixed(2)} °C across {findings.count}{" "}
                observations.
              </p>
            ) : null}
            <p className="hx-kicker">{INSTANTS_DIFF_LABEL}</p>
            <ul className="hx-diffs" data-testid="observed-diffs">
              {findings.pairwise.map((item) => (
                <li key={`${item.fromId}-${item.toId}`}>
                  {item.fromLabel} → {item.toLabel}: {formatDeltaC(item.deltaC)}
                </li>
              ))}
            </ul>
            <details className="hx-method">
              <summary>About these observations</summary>
              <p>{INSTANTS_SUBTITLE}</p>
              <p className="hx-note" data-testid="observed-interval-note">
                {INSTANTS_GAP}
              </p>
            </details>
          </aside>
        </div>
      )}
    </section>
  );
}
