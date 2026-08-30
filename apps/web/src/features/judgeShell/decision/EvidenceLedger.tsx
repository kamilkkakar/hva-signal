import { analysisAreaLabel } from "@/features/selectedAreaStory/identity";
import type { PresentedMatched } from "./types";
import { formatDeltaC } from "./present";
import {
  MATCHED_DISCLOSURE,
  MATCHED_METHOD,
  MATCHED_NOT_CLIMATE,
  SELECT_AREA,
} from "./copy";

type EvidenceLedgerProps = {
  geoid: string | null;
  matched: PresentedMatched;
};

export function EvidenceLedger({ geoid, matched }: EvidenceLedgerProps) {
  const area = analysisAreaLabel(geoid) ?? "No analysis area selected";
  const what =
    matched.status === "AVAILABLE" && matched.change2024vs2022 != null
      ? `Matched-window mean changed ${formatDeltaC(matched.change2024vs2022)} from 2022 to 2024.`
      : matched.reason ?? SELECT_AREA;
  const relative = "Same calendar dates at 03:00 local. Zone-mean TCM. Not a historical-position score.";
  const period = MATCHED_DISCLOSURE;
  const why = MATCHED_METHOD;
  const direction =
    matched.status === "AVAILABLE" ? MATCHED_NOT_CLIMATE : "Direction withheld until the window binds.";
  return (
    <dl className="decision-ledger" data-testid="evidence-ledger" aria-label="Evidence ledger">
      <div>
        <dt>Analysis area</dt>
        <dd>{area}</dd>
      </div>
      <div>
        <dt>What changed</dt>
        <dd>{what}</dd>
      </div>
      <div>
        <dt>Relative to</dt>
        <dd>{relative}</dd>
      </div>
      <div>
        <dt>Period</dt>
        <dd>{period}</dd>
      </div>
      <div>
        <dt>Method</dt>
        <dd>{why}</dd>
      </div>
      <div>
        <dt>Direction</dt>
        <dd>{direction}</dd>
      </div>
    </dl>
  );
}
