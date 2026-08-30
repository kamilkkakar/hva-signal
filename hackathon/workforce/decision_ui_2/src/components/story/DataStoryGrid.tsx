import type { StoryCardId } from "@/contracts";
import { publicStoryCard } from "@/data/publicSurface";
import { DataStoryCard } from "./DataStoryCard";

type DataStoryGridProps = {
  readonly ids: readonly StoryCardId[];
};

export function DataStoryGrid({ ids }: DataStoryGridProps) {
  return (
    <section className="story-grid" aria-label="Data story" data-testid="story-grid">
      {ids.map((id) => (
        <DataStoryCard key={id} card={publicStoryCard(id)} />
      ))}
    </section>
  );
}
