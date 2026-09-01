import { AreaContextBand, type MapMode } from "@/features/areaContext";
import {
  MatchedNightChart,
  ObservedInstantsChart,
} from "@/features/experience";
import { ContextPanel } from "@/features/experience/ContextPanel";
import type { ContextComparison } from "@/features/experience/narrative";
import type { PresentedMatched, PresentedSequence } from "@/features/judgeShell/decision/types";
import type { AnalysisResultStub } from "@/api/analysisJobs";
import type { CrossCityAreaRecord } from "@/features/crossCity/types";
import type { CityId } from "./types";

export type CityEvidenceCapabilities = {
  hasHistoricalMatchedNighttime: boolean;
  hasObservedInstants: boolean;
  hasLocalContext: boolean;
  hasZoneTable: boolean;
  hasResourceInventory: boolean;
};

export function cityEvidenceCapabilities(
  cityId: CityId,
  options?: {
    matchedStatus?: PresentedMatched["status"];
    observedCount?: number;
    contextFactCount?: number;
    zoneCount?: number;
    hasInventory?: boolean;
  },
): CityEvidenceCapabilities {
  const isPhoenix = cityId === "phoenix-az";
  const matchedOk = options?.matchedStatus === "AVAILABLE";
  const observedCount = options?.observedCount ?? 0;
  const zoneCount = options?.zoneCount ?? 0;
  const contextCount = options?.contextFactCount ?? 0;
  return {
    // Historical matched nighttime: real Phoenix data only — never fabricate for LAS/TUC/LA.
    hasHistoricalMatchedNighttime: isPhoenix && matchedOk,
    hasObservedInstants: isPhoenix && observedCount >= 2,
    hasLocalContext: contextCount > 0 || zoneCount > 0,
    hasZoneTable: zoneCount > 0,
    hasResourceInventory: Boolean(isPhoenix && options?.hasInventory),
  };
}

type CityEvidenceSectionsProps = {
  cityId: CityId;
  capabilities: CityEvidenceCapabilities;
  storyStage: "heat" | "context" | "action" | "outlook";
  selectedAreaId: string | null;
  areaLabel: string | null;
  analysisAreaCount: number;
  matched: PresentedMatched;
  observed: PresentedSequence;
  comparisons: readonly ContextComparison[];
  cityRecords: readonly CrossCityAreaRecord[];
  mapMode: MapMode;
  onSelectZone: (geoid: string | null) => void;
  /** Phoenix AreaContextBand wiring */
  phoenixAreaId?: string;
  phoenixResult?: AnalysisResultStub | null;
  onContextZones?: (zones: import("@/features/areaContext").ZoneMapProperties[]) => void;
};

function CrossCityZoneTable({
  records,
  selectedAreaId,
  onSelectZone,
}: {
  records: readonly CrossCityAreaRecord[];
  selectedAreaId: string | null;
  onSelectZone: (geoid: string | null) => void;
}) {
  const showCanopy = records.some((r) => r.metrics.treeCanopyPct != null);
  const showIncome = records.some((r) => r.metrics.medianHouseholdIncomeUsd != null);
  const showOlder = records.some((r) => r.metrics.olderHousingPct != null);

  return (
    <div className="ws-zone-table-wrap" data-testid="view-all-zones-table">
      <table className="ws-zone-table">
        <thead>
          <tr>
            <th>Zone</th>
            <th>Temperature</th>
            {showCanopy ? <th>Canopy</th> : null}
            {showIncome ? <th>Income</th> : null}
            {showOlder ? <th>Older housing</th> : null}
          </tr>
        </thead>
        <tbody>
          {records.map((row) => {
            const selected = row.areaId === selectedAreaId;
            return (
              <tr
                key={row.areaId}
                data-selected={selected ? "true" : "false"}
                className={selected ? "is-selected" : undefined}
              >
                <td>
                  <button
                    type="button"
                    className="ws-zone-row-btn"
                    data-testid={`zone-row-${row.areaId}`}
                    aria-pressed={selected}
                    onClick={() => onSelectZone(row.areaId)}
                  >
                    {row.areaLabel}
                  </button>
                </td>
                <td>
                  {row.metrics.selectedTimeTemperatureC != null
                    ? `${row.metrics.selectedTimeTemperatureC.toFixed(1)} °C`
                    : "—"}
                </td>
                {showCanopy ? (
                  <td>
                    {row.metrics.treeCanopyPct != null
                      ? `${row.metrics.treeCanopyPct.toFixed(0)}%`
                      : "—"}
                  </td>
                ) : null}
                {showIncome ? (
                  <td>
                    {row.metrics.medianHouseholdIncomeUsd != null
                      ? `$${row.metrics.medianHouseholdIncomeUsd.toLocaleString()}`
                      : "—"}
                  </td>
                ) : null}
                {showOlder ? (
                  <td>
                    {row.metrics.olderHousingPct != null
                      ? `${row.metrics.olderHousingPct.toFixed(0)}%`
                      : "—"}
                  </td>
                ) : null}
              </tr>
            );
          })}
        </tbody>
      </table>
    </div>
  );
}

function LocalContextFromRecords({
  record,
}: {
  record: CrossCityAreaRecord | undefined;
}) {
  if (!record) {
    return <p className="hx-note">Select a zone to see published local context.</p>;
  }
  const items: Array<{ label: string; value: string }> = [];
  if (record.metrics.treeCanopyPct != null) {
    items.push({ label: "Tree canopy", value: `${record.metrics.treeCanopyPct.toFixed(0)}%` });
  }
  if (record.metrics.medianHouseholdIncomeUsd != null) {
    items.push({
      label: "Median household income",
      value: `$${record.metrics.medianHouseholdIncomeUsd.toLocaleString()}`,
    });
  }
  if (record.metrics.olderHousingPct != null) {
    items.push({
      label: "Older housing",
      value: `${record.metrics.olderHousingPct.toFixed(0)}% built before 1980`,
    });
  }
  if (items.length === 0) {
    return <p className="hx-note">Local context metrics are not published for this zone.</p>;
  }
  return (
    <dl className="ws-local-context-dl" data-testid="local-context-facts">
      {items.map((item) => (
        <div key={item.label}>
          <dt>{item.label}</dt>
          <dd>{item.value}</dd>
        </div>
      ))}
    </dl>
  );
}

/** Capability-driven below-map evidence. */
export function CityEvidenceSections({
  cityId,
  capabilities,
  storyStage,
  selectedAreaId,
  areaLabel,
  analysisAreaCount,
  matched,
  observed,
  comparisons,
  cityRecords,
  mapMode,
  onSelectZone,
  phoenixAreaId = "phoenix-demo",
  phoenixResult = null,
  onContextZones,
}: CityEvidenceSectionsProps) {
  const selectedRecord = cityRecords.find((r) => r.areaId === selectedAreaId);
  const usePhoenixContextPanel = cityId === "phoenix-az" && comparisons.length > 0;

  return (
    <div className="ws-below-map" data-testid="city-evidence-sections" data-city={cityId}>
      {capabilities.hasHistoricalMatchedNighttime ? (
        <section
          className="ws-analysis-section ws-analysis-section-featured"
          data-testid="matched-night-section"
        >
          <MatchedNightChart
            view={matched}
            areaLabel={areaLabel}
            analysisAreaCount={analysisAreaCount}
          />
        </section>
      ) : null}

      {capabilities.hasObservedInstants ? (
        <details className="ws-analysis-section" data-testid="observed-instants-section">
          <summary>Observed thermal instants</summary>
          <ObservedInstantsChart view={observed} areaLabel={areaLabel} />
        </details>
      ) : null}

      {capabilities.hasLocalContext ? (
        <details
          className="ws-analysis-section"
          data-testid="local-context-section"
          open={storyStage === "context"}
        >
          <summary>Local context</summary>
          {usePhoenixContextPanel ? (
            <ContextPanel
              comparisons={[...comparisons]}
              selectedZoneId={selectedAreaId}
            />
          ) : (
            <LocalContextFromRecords record={selectedRecord} />
          )}
        </details>
      ) : null}

      {capabilities.hasZoneTable ? (
        <details className="ws-analysis-section" data-testid="all-zones-section">
          <summary>View all zones</summary>
          {cityId === "phoenix-az" && onContextZones ? (
            <AreaContextBand
              areaId={phoenixAreaId}
              selectedZoneId={selectedAreaId}
              result={phoenixResult}
              mapMode={mapMode}
              onSelectTract={onSelectZone}
              onContextZones={onContextZones}
            />
          ) : (
            <CrossCityZoneTable
              records={cityRecords}
              selectedAreaId={selectedAreaId}
              onSelectZone={onSelectZone}
            />
          )}
        </details>
      ) : null}
    </div>
  );
}
