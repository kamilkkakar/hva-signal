import { useMemo, useState } from "react";
import {
  CROSS_CITY_HOVER_HALO,
  CROSS_CITY_SELECTION_HALO,
  outlineColorForCity,
} from "./colors";
import {
  axisDomainFromRecords,
  fillColorForMetric,
  metricDomain,
  metricValue,
  radiusFromPopulation,
  type NumericDomain,
} from "./scale";
import {
  CROSS_CITY_DEFAULT_ENCODINGS,
  metricLabel,
  type CrossCityAreaRecord,
  type CrossCityFillKey,
  type CrossCityId,
  type CrossCityMetricKey,
} from "./types";

const SVG_WIDTH = 720;
const SVG_HEIGHT = 420;
const MARGIN = { top: 24, right: 24, bottom: 56, left: 88 };
const FALLBACK_SIZE_RADIUS = 8;
const DESKTOP_STROKE = 2.25;
const MOBILE_STROKE = 2.75;

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
  scaleMode: "comparison" | "focused";
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

function formatOlderHousing(value: number | null): string {
  return value == null ? "Not published" : `${value.toFixed(0)}%`;
}

function formatAxisTick(metric: CrossCityMetricKey, value: number): string {
  if (metric === "selectedTimeTemperatureC") {
    return `${value.toFixed(1)}°`;
  }
  if (metric === "treeCanopyPct" || metric === "olderHousingPct") {
    return `${value.toFixed(0)}%`;
  }
  if (metric === "medianHouseholdIncomeUsd") {
    if (Math.abs(value) >= 1_000_000) {
      return `${(value / 1_000_000).toFixed(1)}M`;
    }
    if (Math.abs(value) >= 1_000) {
      return `${Math.round(value / 1_000)}k`;
    }
  }
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
    point.areaLabel,
    point.cityLabel,
    `Temp: ${formatTemperature(point.metrics.selectedTimeTemperatureC)}`,
    `Canopy: ${formatCanopy(point.metrics.treeCanopyPct)}`,
    `Pop: ${formatPopulation(point.metrics.population)}`,
    `Income: ${formatIncome(point.metrics.medianHouseholdIncomeUsd)}`,
    `Older housing: ${formatOlderHousing(point.metrics.olderHousingPct)}`,
    ...missing,
  ];
}

export function presentBubbleExplorer(
  records: readonly CrossCityAreaRecord[],
  activeCityIds: readonly CrossCityId[],
  selectedCityId: CrossCityId,
  encodings: {
    x: CrossCityMetricKey;
    y: CrossCityMetricKey;
    size: CrossCityMetricKey;
    fill: CrossCityFillKey;
  } = CROSS_CITY_DEFAULT_ENCODINGS,
  options?: {
    forceComparisonScale?: boolean;
  },
): BubbleExplorerView {
  const filtered = records.filter((record) => activeCityIds.includes(record.cityId));
  const isolatedOne = activeCityIds.length === 1;
  const useFocused = isolatedOne && !options?.forceComparisonScale;
  const scaleMode = useFocused ? "focused" : "comparison";

  const xDomain = useFocused
    ? axisDomainFromRecords(filtered, encodings.x)
    : axisDomainFromRecords(records, encodings.x);
  const yDomain = useFocused
    ? axisDomainFromRecords(filtered, encodings.y)
    : axisDomainFromRecords(records, encodings.y);
  // Size + fill stay on shared / fixed scales — never visible-city rescaling.
  const sizeDomain = metricDomain(records, encodings.size === "population" ? "population" : encodings.size);
  const fillDomain =
    encodings.fill === "none" ? null : metricDomain(records, encodings.fill);

  const plotted: BubblePoint[] = [];
  let omittedCount = 0;

  for (const record of filtered) {
    const xValue = metricValue(record, encodings.x);
    const yValue = metricValue(record, encodings.y);
    if (xValue == null || yValue == null) {
      omittedCount += 1;
      continue;
    }
    const sizeValue = metricValue(record, encodings.size);
    const computedRadius = radiusFromPopulation(
      encodings.size === "population" ? sizeValue : sizeValue,
      sizeDomain,
    );
    const fillValue =
      encodings.fill === "none" ? null : metricValue(record, encodings.fill);
    plotted.push({
      ...record,
      cx: scaleX(xValue, xDomain),
      cy: scaleY(yValue, yDomain),
      radius: Math.max(computedRadius ?? FALLBACK_SIZE_RADIUS, 6),
      fill:
        fillColorForMetric(record.cityId, encodings.fill, fillValue, fillDomain) ??
        "url(#hx-cross-city-missing-fill)",
      fillMissing: encodings.fill !== "none" && fillValue == null,
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
    scaleMode,
  };
}

type BubbleExplorerProps = {
  records: readonly CrossCityAreaRecord[];
  activeCityIds: readonly CrossCityId[];
  selectedCityId: CrossCityId;
  xMetric?: CrossCityMetricKey;
  yMetric?: CrossCityMetricKey;
  fillMetric?: CrossCityFillKey;
  forceComparisonScale?: boolean;
  onRequestComparisonScale?: () => void;
  onRequestFocusedScale?: () => void;
};

export function BubbleExplorer({
  records,
  activeCityIds,
  selectedCityId,
  xMetric = CROSS_CITY_DEFAULT_ENCODINGS.x,
  yMetric = CROSS_CITY_DEFAULT_ENCODINGS.y,
  fillMetric = CROSS_CITY_DEFAULT_ENCODINGS.fill,
  forceComparisonScale = false,
  onRequestComparisonScale,
  onRequestFocusedScale,
}: BubbleExplorerProps) {
  const encodings = useMemo(
    () => ({
      x: xMetric,
      y: yMetric,
      size: CROSS_CITY_DEFAULT_ENCODINGS.size,
      fill: fillMetric,
    }),
    [fillMetric, xMetric, yMetric],
  );
  const view = useMemo(
    () =>
      presentBubbleExplorer(records, activeCityIds, selectedCityId, encodings, {
        forceComparisonScale,
      }),
    [activeCityIds, encodings, forceComparisonScale, records, selectedCityId],
  );
  const [activeAreaId, setActiveAreaId] = useState<string | null>(null);
  const [hoveredAreaId, setHoveredAreaId] = useState<string | null>(null);
  const activePoint =
    view.plotted.find((point) => point.areaId === activeAreaId) ??
    view.plotted.find((point) => point.cityId === selectedCityId) ??
    view.plotted[0] ??
    null;

  const strokeBase =
    typeof window !== "undefined" && window.matchMedia("(max-width: 480px)").matches
      ? MOBILE_STROKE
      : DESKTOP_STROKE;

  return (
    <div className="hx-cc-chart-shell" data-testid="cross-city-bubble-explorer">
      <div className="hx-cc-chart-column">
        <svg
          className="hx-chart hx-cc-chart"
          viewBox={`0 0 ${SVG_WIDTH} ${SVG_HEIGHT}`}
          role="img"
          aria-label={`Cross-city scatter plot of ${metricLabel(xMetric)} versus ${metricLabel(yMetric)}`}
          data-scale-mode={view.scaleMode}
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
                  {formatAxisTick(xMetric, tick)}
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
                  {formatAxisTick(yMetric, tick)}
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
            {metricLabel(xMetric)}
          </text>
          <text
            className="hx-axis-title"
            x={18}
            y={(MARGIN.top + SVG_HEIGHT - MARGIN.bottom) / 2}
            textAnchor="middle"
            transform={`rotate(-90 18 ${(MARGIN.top + SVG_HEIGHT - MARGIN.bottom) / 2})`}
          >
            {metricLabel(yMetric)}
          </text>

          {view.plotted.map((point) => {
            const hovered = point.areaId === hoveredAreaId;
            const halo = point.selected
              ? CROSS_CITY_SELECTION_HALO
              : hovered
                ? CROSS_CITY_HOVER_HALO
                : null;
            return (
              <g key={point.areaId}>
                {halo ? (
                  <circle
                    cx={point.cx}
                    cy={point.cy}
                    r={point.radius + 4}
                    fill="none"
                    stroke={halo}
                    strokeWidth={3}
                    opacity={0.95}
                    pointerEvents="none"
                  />
                ) : null}
                <circle
                  cx={point.cx}
                  cy={point.cy}
                  r={point.radius}
                  fill={point.fill}
                  stroke={point.outline}
                  strokeWidth={strokeBase}
                  opacity={point.selected || hovered ? 1 : 0.88}
                  strokeDasharray={point.sizeMissing ? "5 4" : undefined}
                  tabIndex={0}
                  onMouseEnter={() => {
                    setActiveAreaId(point.areaId);
                    setHoveredAreaId(point.areaId);
                  }}
                  onMouseLeave={() => setHoveredAreaId(null)}
                  onFocus={() => setActiveAreaId(point.areaId)}
                  aria-label={bubbleTooltipLines(point).join(". ")}
                />
                {/* Larger invisible hit target when bubbles cluster */}
                <circle
                  cx={point.cx}
                  cy={point.cy}
                  r={Math.max(point.radius, 14)}
                  fill="transparent"
                  onMouseEnter={() => {
                    setActiveAreaId(point.areaId);
                    setHoveredAreaId(point.areaId);
                  }}
                  onMouseLeave={() => setHoveredAreaId(null)}
                  onFocus={() => setActiveAreaId(point.areaId)}
                  tabIndex={-1}
                />
              </g>
            );
          })}
        </svg>

        <div className="hx-cc-chart-meta">
          <p className="hx-note">
            X = {metricLabel(xMetric)} · Y = {metricLabel(yMetric)} · Size = Population · City =
            hue family · Fill intensity ={" "}
            {fillMetric === "none" ? "none (medium city fill)" : metricLabel(fillMetric)}
          </p>
          {view.scaleMode === "focused" ? (
            <p className="hx-note" data-testid="cross-city-focused-scale">
              Focused city scale
              {onRequestComparisonScale ? (
                <>
                  {" "}
                  ·{" "}
                  <button
                    type="button"
                    className="hx-cc-inline-link"
                    onClick={onRequestComparisonScale}
                  >
                    Use comparison scale
                  </button>
                </>
              ) : null}
            </p>
          ) : activeCityIds.length === 1 && forceComparisonScale && onRequestFocusedScale ? (
            <p className="hx-note" data-testid="cross-city-comparison-scale">
              Comparison scale
              {" · "}
              <button type="button" className="hx-cc-inline-link" onClick={onRequestFocusedScale}>
                Use focused city scale
              </button>
            </p>
          ) : null}
          {view.omittedCount > 0 ? (
            <p className="hx-note" data-testid="cross-city-omitted">
              {view.omittedCount} {view.omittedCount === 1 ? "area is" : "areas are"} omitted
              because {metricLabel(xMetric)} or {metricLabel(yMetric)} is not published for this
              comparison.
            </p>
          ) : null}
          {view.filteredCount > 0 && view.plotted.length === 0 ? (
            <p className="hx-note">No areas remain on the plot after the current city filter.</p>
          ) : null}
        </div>
      </div>

      <aside className="hx-cc-tooltip" data-testid="cross-city-tooltip" aria-live="polite">
        {activePoint ? (
          <>
            <p className="hx-kicker">Tooltip</p>
            <h3>{activePoint.areaLabel}</h3>
            <p className="hx-cc-tooltip-city">{activePoint.cityLabel}</p>
            <ul>
              <li>Temp: {formatTemperature(activePoint.metrics.selectedTimeTemperatureC)}</li>
              <li>Canopy: {formatCanopy(activePoint.metrics.treeCanopyPct)}</li>
              <li>Pop: {formatPopulation(activePoint.metrics.population)}</li>
              <li>Income: {formatIncome(activePoint.metrics.medianHouseholdIncomeUsd)}</li>
            </ul>
            {activePoint.cityId === "phoenix-az" ? (
              <p className="hx-cc-tooltip-cta">
                <a className="hx-cc-open-link" href="#happening">
                  Open area analysis →
                </a>
              </p>
            ) : (
              <p className="hx-note">Level-1 comparison only · local analysis not published.</p>
            )}
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
