import { AnalysisDetail } from "@/features/command-center/AnalysisDetail";
import {
  CHIP_CLOCK,
  CHIP_WINDOW,
  CHIP_WINDOW_ID,
  PROVENANCE_L1_ARIA,
  PROVENANCE_L2_SUMMARY,
} from "./copy";
import type { PublicSourceChip } from "./sourceChip";

type ProvenanceBandProps = {
  source: PublicSourceChip;
  clockDate?: string | null;
};

export function ProvenanceBand({ source, clockDate }: ProvenanceBandProps) {
  const clock = clockDate ? `${clockDate} ${CHIP_CLOCK}` : `${CHIP_CLOCK} AOI-local`;

  return (
    <section className="judge-provenance" aria-label={PROVENANCE_L1_ARIA}>
      <ul className="judge-chips" data-testid="provenance-l1">
        <li>source {source}</li>
        <li>clock {clock}</li>
        <li>
          window {CHIP_WINDOW_ID} · {CHIP_WINDOW}
        </li>
        <li>coverage analysis window</li>
        <li>mode historical unusualness</li>
      </ul>
      <details className="judge-provenance-l2" data-testid="provenance-l2">
        <summary>{PROVENANCE_L2_SUMMARY}</summary>
        <AnalysisDetail />
      </details>
    </section>
  );
}
