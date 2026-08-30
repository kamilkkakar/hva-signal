import type { SignalAView } from "./types";

type SigAQuestionProps = {
  view: SignalAView;
};

export function SigAQuestion({ view }: SigAQuestionProps) {
  return (
    <header className="siga-question">
      <p className="kicker">Signal A</p>
      <h2>{view.title}</h2>
      <p className="siga-chip" data-testid="siga-chip">
        {view.chip}
      </p>
      <p data-testid="siga-question-primary">{view.questionPrimary}</p>
      <p data-testid="siga-question-gate">{view.questionGate}</p>
      <p className="siga-one-sentence">{view.oneSentence}</p>
      <p className="siga-independence">{view.independence}</p>
    </header>
  );
}
