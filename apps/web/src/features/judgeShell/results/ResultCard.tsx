import type { ResultCardModel } from "./types";

export type ResultCardProps = {
  card: ResultCardModel;
};

export function ResultCard({ card }: ResultCardProps) {
  return (
    <article
      className="result-card"
      data-testid={`thermal-card-${card.id}`}
      data-result-id={card.id}
    >
      <p className="result-card-kicker">{card.kicker}</p>
      <h2 className="result-card-title">{card.title}</h2>
      <p className="result-card-question" data-testid={`result-card-${card.id}-question`}>
        {card.question}
      </p>
      <p
        className="result-card-stamp"
        data-testid={card.id === "a" ? "signal-a-stamp" : "signal-b-stamp"}
      >
        {card.stamp}
      </p>
      <p className="result-card-message" data-testid={`result-card-${card.id}-message`}>
        {card.message}
      </p>
      {card.values.length > 0 && (
        <dl className="result-card-values" data-testid={`result-card-${card.id}-values`}>
          {card.values.map((item) => (
            <div key={item.label} className="result-card-value">
              <dt>{item.label}</dt>
              <dd>{item.value}</dd>
            </div>
          ))}
        </dl>
      )}
    </article>
  );
}
