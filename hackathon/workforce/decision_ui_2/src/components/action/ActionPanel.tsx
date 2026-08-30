import type { QuestionId } from "@/contracts";
import { publicAction } from "@/data/publicSurface";

type ActionPanelProps = {
  readonly questionId: QuestionId;
};

const BLOCKS = [
  ["evidenceShows", "What the evidence shows"],
  ["whyItMatters", "Why it matters"],
  ["direction", "Direction"],
  ["verifyNext", "What to verify next"],
  ["doesNotEstablish", "What this does not establish"],
] as const;

export function ActionPanel({ questionId }: ActionPanelProps) {
  const model = publicAction(questionId);
  return (
    <aside className="action" aria-label="Action and direction" data-testid="action-panel">
      <h3>Direction</h3>
      {BLOCKS.map(([key, title]) => (
        <section key={key} className="action-block">
          <h4>{title}</h4>
          <ul>
            {model[key].map((line) => (
              <li key={line}>{line}</li>
            ))}
          </ul>
        </section>
      ))}
    </aside>
  );
}
