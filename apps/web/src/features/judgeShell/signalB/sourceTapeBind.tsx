import { SourceTape } from "@/features/command-center/SourceTape";
import { PerSignalProvenance } from "@/features/provenance/PerSignalProvenance";
import { refuseCollapsedSourceTape } from "@/features/provenance/banner";
import type { PublicSignalProvenance } from "@/features/provenance/types";
import type { SourceBannerLabel } from "@/utils/sourceBanner";
import { P1_LANDING_SELECTED_TIME_REQUESTED } from "./publicBGate";

export { P1_LANDING_SELECTED_TIME_REQUESTED };

export type CommandCenterProvenanceMode = "a-only-tape" | "per-signal";

export function commandCenterProvenanceMode(
  selectedTimeRequested: boolean,
): CommandCenterProvenanceMode {
  return selectedTimeRequested ? "per-signal" : "a-only-tape";
}

type CommandCenterProvenanceProps = {
  selectedTimeRequested: boolean;
  aOnlyBanner: SourceBannerLabel;
  historical?: PublicSignalProvenance | null;
  selectedTime?: PublicSignalProvenance | null;
};

/**
 * Q7 bind from SIG-B 379f037. A-only jobs keep the landing SourceTape.
 * When Signal B is requested, A and B never share one tape.
 * P1 landing does not request B.
 */
export function CommandCenterProvenance({
  selectedTimeRequested,
  aOnlyBanner,
  historical = null,
  selectedTime = null,
}: CommandCenterProvenanceProps) {
  if (commandCenterProvenanceMode(selectedTimeRequested) === "per-signal") {
    return (
      <PerSignalProvenance
        historical={historical}
        selectedTime={selectedTime}
        historicalRequested={historical != null}
        selectedTimeRequested
      />
    );
  }
  return <SourceTape active={aOnlyBanner} />;
}

export function refuseCollapsedCommandCenterTape(): never {
  return refuseCollapsedSourceTape();
}
