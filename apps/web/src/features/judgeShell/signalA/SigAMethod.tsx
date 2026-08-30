import type { SignalAView } from "./types";

type SigAMethodProps = {
  view: SignalAView;
};

export function SigAMethod({ view }: SigAMethodProps) {
  return (
    <details className="siga-method" data-testid="siga-method">
      <summary>{view.method.title}</summary>
      <p data-testid="siga-method-qa">{view.method.q_A}</p>
      <p data-testid="siga-method-d8">{view.method.decision8}</p>
      <p data-testid="siga-method-s">{view.method.S}</p>
    </details>
  );
}
