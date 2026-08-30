import { PRODUCT_QUESTIONS, type ProductQuestionId } from "./questions";

type QuestionNavProps = {
  activeId: ProductQuestionId;
  onSelect: (id: ProductQuestionId) => void;
};

export function QuestionNav({ activeId, onSelect }: QuestionNavProps) {
  return (
    <nav className="decision-questions" aria-label="Product questions" data-testid="decision-questions">
      <ol>
        {PRODUCT_QUESTIONS.map((question) => (
          <li key={question.id}>
            <button
              type="button"
              data-active={question.id === activeId ? "true" : "false"}
              onClick={() => onSelect(question.id)}
            >
              <span className="decision-q-index">{question.index}</span>
              <span className="decision-q-prompt">{question.prompt}</span>
            </button>
          </li>
        ))}
      </ol>
    </nav>
  );
}
