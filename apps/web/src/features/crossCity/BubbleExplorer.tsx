import { useMemo, useState } from "react";
import { outlineColorForCity } from "./colors";
import {
  globalFillColor,
  metricDomain,
  metricValue,
  radiusFromPopulation,
  type NumericDomain,
} from "./scale";
import type { CrossCityAreaRecord, CrossCityId, CrossCityMetricKey } from "./types";

const SVG_WIDTH = 720;
const SVG_HEIGHT = 420;
const MARGIN = { top: 24, right: 24, bottom: 56, left: 88 };
const FALLBACK_SIZE_RADIUS = 8;

type BubblePoint = CrossCityAreaRecord & {
  cx: number;
  cy: number;
  radius: number;
  fill: string;
  fillMissing: boolean;
  sizeMissing: boolean;
  outline: string;
  selected: boolean;
};

export type BubbleExplorerView = {
  plotted: BubblePoint[];
  omittedCount: number;
  filteredCount: number;
  xDomain: NumericDomain | null;
  yDomain: NumericDomain | null;
};

function scaleX(value: number, domain: NumericDomain | null): number {
  const left = MARGIN.left;
  const right = SVG_WIDTH - MARGIN.right;
  if (!domain) {
    return (left + right) / 2;
  }
  const span = domain.max - domain.min;
  if (span <= 0) {
    return (left + right) / 2;
  }
  return left + ((value - domain.min) / span) * (right - left);
}

function scaleY(value: number, domain: NumericDomain | null): number {
  const top = MARGIN.top;
  const bottom = SVG_HEIGHT - MARGIN.bottom;
  if (!domain) {
    return (top + bottom) / 2;
  }
  const span = domain.max - domain.min;
  if (span <= 0) {
    return (top + bottom) / 2;
  }
  return bottom - ((value - domain.min) / span) * (bottom - top);
}

function tickValues(domain: NumericDomain | null, count: number): number[] {
  if (!domain) {
    return [];
  }
  if (domain.max === domain.min) {
    return [domain.min];
  }
  const step = (domain.max - domain.min) / Math.max(count - 1, 1);
  return Array.from({ length: count }, (_, index) => domain.min + step * index);
}

function formatTemperature(value: number | null): string {
  return value == null ? "Not published" : `${value.toFixed(1)} °C`;
}

function formatIncome(value: number | null): string {
  return value == null
    ? "Not published"
    : new Intl.NumberFormat("en-US", {
        style: "currency",
        currency: "USD",
        maximumFractionDigits: 0,
      }).format(value);
}

function formatPopulation(value: number | null): string {
  return value == null
    ? "Not published"
    : new Intl.NumberFormat("en-US", { maximumFractionDigits: 0 }).format(value);
}

function formatCanopy(value: number | null): string {
  return value == null ? "Not published" : `${value.toFixed(1)}%`;
}

function formatXAxisTick(value: number): string {
  return `${value.toFixed(1)}°`;
}

function formatYAxisTick(value: number): string {
  if (Math.abs(value) >= 1_000_000) {
    return `${(value / 1_000_000).toFixed(1)}M`;
  }
  if (Math.abs(value) >= 1_000) {
    return `${Math.round(value / 1_000)}k`;
  }
  return `${Math.round(value)}`;
}

export function bubbleTooltipLines(point: CrossCityAreaRecord): string[] {
  const missing: string[] = [];
  if (point.metrics.treeCanopyPct == null) {
    missing.push("Tree canopy fill not published for this area.");
  }
  if (point.metrics.population == null) {
    missing.push("Population is not published, so bubble size uses a fallback marker.");
  }
  return [
    point.cityLabel,
    point.areaLabel,
    `Selected-time temperature: ${formatTemperature(point.metrics.selectedTimeTemperatureC)}`,
    `Median household income: ${formatIncome(point.metrics.medianHouseholdIncomeUsd)}`,
    `Population: ${formatPopulation(point.metrics.population)}`,
    `Tree canopy: ${formatCanopy(point.metrics.treeCanopyPct)}`,
    ...missing,
  ];
}

export function presentBubbleExplorer(
  records: readonly CrossCityAreaRecord[],
  activeCityIds: readonly CrossCityId[],
  selectedCityId: CrossCityId,
  fillMetric: CrossCityMetricKey = "treeCanopyPct",
): BubbleExplorerView {
  const xDomain = metricDomain(records, "selectedTimeTemperatureC");
  const yDomain = metricDomain(records, "medianHouseholdIncomeUsd");
  const sizeDomain = metricDomain(records, "population");
  const fillDomain = metricDomain(records, fillMetric);
  const filtered = records.filter((record) => activeCityIds.includes(record.cityId));
  const plotted: BubblePoint[] = [];
  let omittedCount = 0;

  for (const record of filtered) {
    const xValue = record.metrics.selectedTimeTemperatureC;
    const yValue = record.metrics.medianHouseholdIncomeUsd;
    if (xValue == null || yValue == null) {
      omittedCount += 1;
      continue;
    }
    const computedRadius = radiusFromPopulation(record.metrics.population, sizeDomain);
    const fillValue = metricValue(record, fillMetric);
    plotted.push({
      ...record,
      cx: scaleX(xValue, xDomain),
      cy: scaleY(yValue, yDomain),
      radius: computedRadius ?? FALLBACK_SIZE_RADIUS,
      fill: globalFillColor(fillValue, fillDomain) ?? "url(#hx-cross-city-missing-fill)",
      fillMissing: fillValue == null,
      sizeMissing: computedRadius == null,
      outline: outlineColorForCity(record.cityId),
      selected: record.cityId === selectedCityId,
    });
  }

  return {
    plotted,
    omittedCount,
    filteredCount: filtered.length,
    xDomain,
    yDomain,
  };
}

type BubbleExplorerProps = {
  records: readonly CrossCityAreaRecord[];
  activeCityIds: readonly CrossCityId[];
  selectedCityId: CrossCityId;
  fillMetric?: CrossCityMetricKey;
};

export function BubbleExplorer({
  records,
  activeCityIds,
  selectedCityId,
  fillMetric = "treeCanopyPct",
}: BubbleExplorerProps) {
  const view = useMemo(
    () => presentBubbleExplorer(records, activeCityIds, selectedCityId, fillMetric),
    [activeCityIds, fillMetric, records, selectedCityId],
  );
  const [activeAreaId, setActiveAreaId] = useState<string | null>(null);
  const activePoint =
    view.plotted.find((point) => point.areaId === activeAreaId) ??
    view.plotted.find((point) => point.cityId === selectedCityId) ??
    view.plotted[0] ??
    null;

  return (
    <div className="hx-cc-chart-shell" data-testid="cross-city-bubble-explorer">
      <svg
        className="hx-chart hx-cc-chart"
        viewBox={`0 0 ${SVG_WIDTH} ${SVG_HEIGHT}`}
        role="img"
        aria-label="Cross-city scatter plot of selected-time temperature and median household income"
      >
        <defs>
          <pattern
            id="hx-cross-city-missing-fill"
            width="8"
            height="8"
            patternUnits="userSpaceOnUse"
            patternTransform="rotate(45)"
          >
            <rect width="8" height="8" fill="#f7f8f5" />
            <line x1="0" y1="0" x2="0" y2="8" stroke="#9ca3af" strokeWidth="2" />
          </pattern>
        </defs>

        <line
          className="hx-axis-line"
          x1={MARGIN.left}
          y1={SVG_HEIGHT - MARGIN.bottom}
          x2={SVG_WIDTH - MARGIN.right}
          y2={SVG_HEIGHT - MARGIN.bottom}
        />
        <line
          className="hx-axis-line"
          x1={MARGIN.left}
          y1={MARGIN.top}
          x2={MARGIN.left}
          y2={SVG_HEIGHT - MARGIN.bottom}
        />

        {tickValues(view.xDomain, 5).map((tick) => {
          const x = scaleX(tick, view.xDomain);
          return (
            <g key={`x-${tick}`}>
              <line
                className="hx-axis-tick"
                x1={x}
                y1={SVG_HEIGHT - MARGIN.bottom}
                x2={x}
                y2={SVG_HEIGHT - MARGIN.bottom + 6}
              />
              <text
                className="hx-axis-label"
                x={x}
                y={SVG_HEIGHT - MARGIN.bottom + 20}
                textAnchor="middle"
              >
                {formatXAxisTick(tick)}
              </text>
            </g>
          );
        })}

        {tickValues(view.yDomain, 5).map((tick) => {
          const y = scaleY(tick, view.yDomain);
          return (
            <g key={`y-${tick}`}>
              <line className="hx-axis-tick" x1={MARGIN.left - 6} y1={y} x2={MARGIN.left} y2={y} />
              <text className="hx-axis-label" x={MARGIN.left - 10} y={y + 4} textAnchor="end">
                {formatYAxisTick(tick)}
              </text>
            </g>
          );
        })}

        <text
          className="hx-axis-title"
          x={(MARGIN.left + SVG_WIDTH - MARGIN.right) / 2}
          y={SVG_HEIGHT - 12}
          textAnchor="middle"
        >
          Selected-time temperature (°C)
        </text>
        <text
          className="hx-axis-title"
          x={18}
          y={(MARGIN.top + SVG_HEIGHT - MARGIN.bottom) / 2}
          textAnchor="middle"
          transform={`rotate(-90 18 ${(MARGIN.top + SVG_HEIGHT - MARGIN.bottom) / 2})`}
        >
          Median household income
        </text>

        {view.plotted.map((point) => (
          <circle
            key={point.areaId}
            cx={point.cx}
            cy={point.cy}
            r={point.radius}
            fill={point.fill}
            stroke={point.outline}
            strokeWidth={point.selected ? 3.5 : 2}
            opacity={point.selected ? 1 : 0.9}
            strokeDasharray={point.sizeMissing ? "5 4" : undefined}
            tabIndex={0}
            onMouseEnter={() => setActiveAreaId(point.areaId)}
            onFocus={() => setActiveAreaId(point.areaId)}
            aria-label={bubbleTooltipLines(point).join(" ")}
          />
        ))}
      </svg>

      <div className="hx-cc-chart-meta">
        <p className="hx-note">
          X = selected-time temperature (°C) · Y = median household income · Size = population ·
          Fill = {fillMetric === "treeCanopyPct" ? "tree canopy" : "selected-time temperature"} ·
          Outline = city
        </p>
        {view.omittedCount > 0 ? (
          <p className="hx-note" data-testid="cross-city-omitted">
            {view.omittedCount} {view.omittedCount === 1 ? "area is" : "areas are"} omitted
            because selected-time temperature or median household income is not published for this
            comparison.
          </p>
        ) : null}
        {view.filteredCount > 0 && view.plotted.length === 0 ? (
          <p className="hx-note">No areas remain on the plot after the current city filter.</p>
        ) : null}
      </div>

      <aside className="hx-cc-tooltip" data-testid="cross-city-tooltip" aria-live="polite">
        {activePoint ? (
          <>
            <p className="hx-kicker">Tooltip</p>
            <h3>{activePoint.areaLabel}</h3>
            <p className="hx-cc-tooltip-city">{activePoint.cityLabel}</p>
            <ul>
              {bubbleTooltipLines(activePoint).slice(2).map((line) => (
                <li key={line}>{line}</li>
              ))}
            </ul>
          </>
        ) : (
          <>
            <p className="hx-kicker">Tooltip</p>
            <p>Hover or focus a bubble to inspect the published comparison values.</p>
          </>
        )}
      </aside>
    </div>
  );
}
