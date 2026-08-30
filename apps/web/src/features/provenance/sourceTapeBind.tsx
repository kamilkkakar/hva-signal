import { refuseCollapsedSourceTape } from "./banner";
import {
  bindProvenanceFromJob,
  type BoundProvenance,
  type FromJobInput,
} from "./fromJob";
import { projectLevel1, type PublicLevel1 } from "./level1";
import type { PublicSignalProvenance } from "./types";
import "./sourceTapeBind.css";

/**
 * Drop-in for I-UX-SHELL. Replaces the live-wins header tape.
 *
 *   import { CommandCenterProvenanceHeader } from "@/features/provenance";
 *   <CommandCenterProvenanceHeader job={snapshot} selectedTimeSection={snapshot.selected_time} />
 *
 * Never calls the utils mapper. Illegal pairs throw.
 * A-only landing stays one Level 1 rail. When B is requested, two rails.
 */
export const P1_LANDING_SELECTED_TIME_REQUESTED = false;

export type CommandCenterProvenanceMode = "a-only-level1" | "per-signal";

export function commandCenterProvenanceMode(
  selectedTimeRequested: boolean,
): CommandCenterProvenanceMode {
  return selectedTimeRequested ? "per-signal" : "a-only-level1";
}

export type CommandCenterProvenanceHeaderProps = FromJobInput;

const IDLE_A: PublicSignalProvenance = {
  signal_kind: "historical_normalized",
  source: null,
  data_status: "unavailable",
};

export function headerLevel1Line(level1: PublicLevel1): string {
  return `${level1.source} · ${level1.observation} · ${level1.evidenceMode}`;
}

function HeaderRail({
  view,
  coverage,
  areaId,
  testId,
}: {
  view: PublicSignalProvenance;
  coverage: BoundProvenance["historicalCoverage"];
  areaId: string | null;
  testId: string;
}) {
  const level1 = projectLevel1({ view, coverage, areaId });
  const showReference = view.signal_kind === "historical_normalized";

  return (
    <article
      className="prov-header-rail"
      data-testid={testId}
      data-signal-kind={view.signal_kind}
      data-evidence-mode={level1.evidenceMode}
      data-reference={showReference ? "true" : "false"}
    >
      <p className="prov-header-title">{level1.title}</p>
      <p className="prov-header-line">{headerLevel1Line(level1)}</p>
    </article>
  );
}

export function CommandCenterProvenanceHeader(props: CommandCenterProvenanceHeaderProps) {
  const bound = bindProvenanceFromJob(props);
  const mode = commandCenterProvenanceMode(bound.selectedTimeRequested);
  const historical =
    bound.historical ?? (bound.selectedTimeRequested ? null : IDLE_A);
  const showA = bound.historicalRequested && historical != null;
  const showB = bound.selectedTimeRequested && bound.selectedTime != null;

  return (
    <div
      className="prov-header"
      data-testid="command-center-provenance-header"
      data-collapsed="false"
      data-mode={mode}
      data-legacy-thermal-source={bound.legacyThermalSource ?? ""}
    >
      {showA && historical != null && (
        <HeaderRail
          view={historical}
          coverage={bound.historicalCoverage}
          areaId={bound.historicalAreaId}
          testId="signal-a-header-provenance"
        />
      )}
      {showB && bound.selectedTime != null && (
        <HeaderRail
          view={bound.selectedTime}
          coverage={bound.selectedTimeCoverage}
          areaId={bound.selectedTimeAreaId}
          testId="signal-b-header-provenance"
        />
      )}
    </div>
  );
}

/** SIG-B seam name. Same drop-in; live-wins tape is not used. */
export const CommandCenterProvenance = CommandCenterProvenanceHeader;

export function refuseCollapsedCommandCenterTape(): never {
  return refuseCollapsedSourceTape();
}
