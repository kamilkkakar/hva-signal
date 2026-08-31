export type {
  NarrativeSynthesis,
  NarrativeSynthesisInput,
  DominantPatternId,
  EvidenceSignal,
  ContextComparison,
  PreparednessEvidenceStatus,
  SpatialDiffStatus,
} from "./types";
export { synthesizeNarrative } from "./synthesize";
export { resolveDominantPattern, interpretContextFact, PATTERN_COPY, formatDeltaPhrase } from "./pattern";
