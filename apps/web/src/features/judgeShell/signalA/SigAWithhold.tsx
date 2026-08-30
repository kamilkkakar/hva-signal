import type { SignalAView } from "./types";

type SigAWithholdProps = {
  view: SignalAView;
};

export function SigAWithhold({ view }: SigAWithholdProps) {
  if (view.kind !== "order_withheld" || !view.featureLine) {
    return null;
  }
  return (
    <p
      className="siga-feature"
      data-testid="siga-withhold-feature"
      data-insufficient-is-feature="true"
    >
      {view.featureLine}
    </p>
  );
}
