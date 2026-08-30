import type { SignalAView } from "./types";

type SigAOrderStampProps = {
  view: SignalAView;
};

export function SigAOrderStamp({ view }: SigAOrderStampProps) {
  if (!view.stamp) {
    return null;
  }
  return (
    <p
      className="siga-stamp evidence-stamp"
      data-testid="siga-stamp"
      data-siga-kind={view.kind}
      data-siga-tone={view.tone}
    >
      {view.stamp}
    </p>
  );
}
