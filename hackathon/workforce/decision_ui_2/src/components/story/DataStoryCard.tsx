import type { DataStoryCardModel } from "@/contracts";
import { fieldNote, isReady } from "@/contracts";
import { COMPARED_PENDING, COVERAGE_PENDING, INTERPRET_PENDING, MAGNITUDE_PENDING } from "@/ia/copy";

type DataStoryCardProps = {
  readonly card: DataStoryCardModel;
};

export function DataStoryCard({ card }: DataStoryCardProps) {
  const magnitude = isReady(card.magnitude) ? card.magnitude.value : null;
  const compared = isReady(card.comparedWith) ? card.comparedWith.value : null;
  const coverage = isReady(card.coverage) ? card.coverage.value : null;
  const interpretation = isReady(card.interpretation) ? card.interpretation.value : null;
  const direction = isReady(card.direction) ? card.direction.value : null;
  const pending = !magnitude;

  return (
    <article className="story-card" data-testid={`story-card-${card.id}`} data-pending={pending}>
      <h3>{card.title}</h3>
      {magnitude ? (
        <p className="story-magnitude">
          {magnitude.display}
          <span className="story-unit">{magnitude.unit}</span>
        </p>
      ) : (
        <p className="story-magnitude" data-pending="true">
          {MAGNITUDE_PENDING}
        </p>
      )}
      <dl className="meta-row">
        <div>
          <dt>Compared with</dt>
          <dd>{compared ?? COMPARED_PENDING}</dd>
        </div>
        <div>
          <dt>Coverage</dt>
          <dd>{coverage ?? COVERAGE_PENDING}</dd>
        </div>
        <div>
          <dt>Interpretation</dt>
          <dd>{interpretation ?? INTERPRET_PENDING}</dd>
        </div>
        <div>
          <dt>Direction</dt>
          <dd>{direction ?? fieldNote(card.direction)}</dd>
        </div>
      </dl>
    </article>
  );
}
