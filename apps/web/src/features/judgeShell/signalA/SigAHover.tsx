import { signalAHoverLine } from "./presentation";
import type { SignalAKind } from "./types";

export { signalAHoverLine };

type SigAHoverProps = {
  kind: SignalAKind;
  zoneId: string;
  order: number;
};

export function SigAHover({ kind, zoneId, order }: SigAHoverProps) {
  const line = signalAHoverLine({ kind, zoneId, order });
  if (!line) {
    return null;
  }
  return (
    <p className="siga-hover" data-testid="siga-hover">
      {line}
    </p>
  );
}
