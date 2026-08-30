import { projectLevel1, type CoverageCount } from "./level1";
import { projectLevel2, type Level2Extras } from "./level2";
import { legacyThermalSource } from "./rail";
import type { PublicSignalProvenance, SignalKind } from "./types";
import "./publicExperience.css";

export type PublicProvenanceExperienceProps = {
  historical?: PublicSignalProvenance | null;
  selectedTime?: PublicSignalProvenance | null;
  historicalRequested?: boolean;
  selectedTimeRequested?: boolean;
  historicalCoverage?: CoverageCount | null;
  selectedTimeCoverage?: CoverageCount | null;
  historicalAreaId?: string | null;
  selectedTimeAreaId?: string | null;
  historicalLevel2Extras?: Level2Extras;
  selectedTimeLevel2Extras?: Level2Extras;
  active?: SignalKind | "both";
};

function ProvenanceRail({
  view,
  testId,
  coverage,
  areaId,
  extras,
}: {
  view: PublicSignalProvenance;
  testId: string;
  coverage?: CoverageCount | null;
  areaId?: string | null;
  extras?: Level2Extras;
}) {
  const level1 = projectLevel1({ view, coverage, areaId });
  const level2 = projectLevel2(view, extras);
  const showReference = view.signal_kind === "historical_normalized";

  return (
    <article
      className="prov-rail"
      data-testid={testId}
      data-signal-kind={view.signal_kind}
      data-evidence-mode={level1.evidenceMode}
      data-reference={showReference ? "true" : "false"}
    >
      <h3 className="prov-title">{level1.title}</h3>
      <dl className="prov-level1" data-testid={`${testId}-level1`}>
        <div>
          <dt>Source</dt>
          <dd>{level1.source}</dd>
        </div>
        <div>
          <dt>Observation</dt>
          <dd>{level1.observation}</dd>
        </div>
        <div>
          <dt>Analysis geography</dt>
          <dd>{level1.geography}</dd>
        </div>
        <div>
          <dt>Coverage</dt>
          <dd>{level1.coverage}</dd>
        </div>
        <div>
          <dt>Evidence mode</dt>
          <dd>{level1.evidenceMode}</dd>
        </div>
      </dl>
      <details className="prov-level2" data-testid={`${testId}-level2`}>
        <summary>Method and versions</summary>
        <dl>
          {level2.map((row) => (
            <div key={row.key} data-kind={row.kind} data-row={row.key}>
              <dt>{row.label}</dt>
              <dd className={row.kind === "hash" ? "prov-hash" : undefined}>{row.value}</dd>
            </div>
          ))}
        </dl>
      </details>
    </article>
  );
}

export function PublicProvenanceExperience({
  historical,
  selectedTime,
  historicalRequested = historical != null,
  selectedTimeRequested = selectedTime != null,
  historicalCoverage = null,
  selectedTimeCoverage = null,
  historicalAreaId = null,
  selectedTimeAreaId = null,
  historicalLevel2Extras,
  selectedTimeLevel2Extras,
  active = "both",
}: PublicProvenanceExperienceProps) {
  const showA =
    historicalRequested &&
    historical != null &&
    (active === "both" || active === "historical_normalized");
  const showB =
    selectedTimeRequested &&
    selectedTime != null &&
    (active === "both" || active === "selected_time_snapshot");

  return (
    <div
      className="prov-experience"
      data-testid="public-provenance-experience"
      data-collapsed="false"
      data-legacy-thermal-source={
        legacyThermalSource({
          selectedTimeRequested,
          historicalSource: historical?.source,
        }) ?? ""
      }
    >
      {showA && historical != null && (
        <ProvenanceRail
          view={historical}
          testId="signal-a-public-provenance"
          coverage={historicalCoverage}
          areaId={historicalAreaId}
          extras={historicalLevel2Extras}
        />
      )}
      {showB && selectedTime != null && (
        <ProvenanceRail
          view={selectedTime}
          testId="signal-b-public-provenance"
          coverage={selectedTimeCoverage}
          areaId={selectedTimeAreaId}
          extras={selectedTimeLevel2Extras}
        />
      )}
    </div>
  );
}
