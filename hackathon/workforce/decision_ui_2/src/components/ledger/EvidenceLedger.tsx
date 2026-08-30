import {
  LEDGER_DIRECTION,
  LEDGER_PENDING_DIRECTION,
  LEDGER_PENDING_PERIOD,
  LEDGER_PENDING_RELATIVE,
  LEDGER_PENDING_WHAT,
  LEDGER_PENDING_WHY,
  LEDGER_PERIOD,
  LEDGER_RELATIVE,
  LEDGER_WHAT,
  LEDGER_WHY,
} from "@/ia/copy";

const CELLS = [
  { id: "what", label: LEDGER_WHAT, value: LEDGER_PENDING_WHAT },
  { id: "relative", label: LEDGER_RELATIVE, value: LEDGER_PENDING_RELATIVE },
  { id: "period", label: LEDGER_PERIOD, value: LEDGER_PENDING_PERIOD },
  { id: "why", label: LEDGER_WHY, value: LEDGER_PENDING_WHY },
  { id: "direction", label: LEDGER_DIRECTION, value: LEDGER_PENDING_DIRECTION },
] as const;

export function EvidenceLedger() {
  return (
    <dl className="ledger" data-testid="evidence-ledger" aria-label="Evidence ledger">
      {CELLS.map((cell) => (
        <div key={cell.id} className="ledger-cell">
          <dt>{cell.label}</dt>
          <dd>{cell.value}</dd>
        </div>
      ))}
    </dl>
  );
}
