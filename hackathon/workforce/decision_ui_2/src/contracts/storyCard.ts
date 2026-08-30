import type { BoundField } from "./availability";

export type StoryMagnitude = {
  readonly display: string;
  readonly unit: string;
};

export type DataStoryCardModel = {
  readonly id: string;
  readonly title: string;
  readonly magnitude: BoundField<StoryMagnitude>;
  readonly comparedWith: BoundField<string>;
  readonly coverage: BoundField<string>;
  readonly interpretation: BoundField<string>;
  readonly direction: BoundField<string>;
};
