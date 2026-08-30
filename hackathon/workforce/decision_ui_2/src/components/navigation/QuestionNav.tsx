import type { QuestionId } from "@/contracts";
import { QUESTIONS } from "@/ia/questions";

type QuestionNavProps = {
  readonly activeId: QuestionId;
  readonly onSelect: (id: QuestionId) => void;
};

export function QuestionNav({ activeId, onSelect }: QuestionNavProps) {
  return (
    <nav className="spine" aria-label="Decision questions" data-testid="question-nav">
      <p className="spine-label">Ask</p>
      <ol className="spine-list">
        {QUESTIONS.map((question) => (
          <li key={question.id}>
            <button
              type="button"
              className="spine-btn"
              aria-current={activeId === question.id ? "page" : undefined}
              onClick={() => onSelect(question.id)}
              data-testid={`question-${question.id}`}
            >
              <span className="spine-index">{String(question.index).padStart(2, "0")}</span>
              <span className="spine-text">{question.prompt}</span>
            </button>
          </li>
        ))}
      </ol>
    </nav>
  );
}
