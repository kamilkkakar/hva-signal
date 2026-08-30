import { signalProvenanceBanner } from "./banner";
import { historicalLines, selectedTimeLines } from "./lines";
import {
  decision8PanelPermitted,
  legacyThermalSource,
  qaHoverPermitted,
  referenceLinePermitted,
} from "./rail";
import type { PublicSignalProvenance, SignalKind } from "./types";

type PerSignalProvenanceProps = {
  historical?: PublicSignalProvenance | null;
  selectedTime?: PublicSignalProvenance | null;
  historicalRequested?: boolean;
  selectedTimeRequested?: boolean;
  active?: SignalKind | "both";
};

function SignalRail({
  view,
  testId,
}: {
  view: PublicSignalProvenance;
  testId: string;
}) {
  const { banner, pathStem } = signalProvenanceBanner({
    source: view.source,
    dataStatus: view.data_status,
  });
  const lines =
    view.signal_kind === "historical_normalized"
      ? historicalLines(view)
      : selectedTimeLines(view);
  const showDecision8 = decision8PanelPermitted(view.signal_kind);
  const showReference = referenceLinePermitted(view.signal_kind);
  const showQa = qaHoverPermitted(view.signal_kind);

  return (
    <section
      data-testid={testId}
      data-signal-kind={view.signal_kind}
      data-banner={banner}
      data-path-stem={pathStem ?? ""}
      data-decision8={showDecision8 ? "true" : "false"}
      data-reference={showReference ? "true" : "false"}
      data-qa-hover={showQa ? "true" : "false"}
    >
      {lines.map((line) => (
        <p key={line}>{line}</p>
      ))}
      {showDecision8 && view.reference_version != null && (
        <p data-testid="decision8-reference-version">{view.reference_version}</p>
      )}
    </section>
  );
}

export function PerSignalProvenance({
  historical,
  selectedTime,
  historicalRequested = historical != null,
  selectedTimeRequested = selectedTime != null,
  active = "both",
}: PerSignalProvenanceProps) {
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
      data-testid="per-signal-provenance"
      data-collapsed="false"
      data-legacy-thermal-source={
        legacyThermalSource({
          selectedTimeRequested,
          historicalSource: historical?.source,
        }) ?? ""
      }
    >
      {showA && historical != null && (
        <SignalRail view={historical} testId="signal-a-provenance" />
      )}
      {showB && selectedTime != null && (
        <SignalRail view={selectedTime} testId="signal-b-provenance" />
      )}
    </div>
  );
}
