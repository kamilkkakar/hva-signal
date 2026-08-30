import type { AnalysisJobPayload } from "@/api/analysisJobs";
import { presentResultStory, ResultStory } from "./resultStory";

type ResultStoryBandProps = {
  snapshot: AnalysisJobPayload | null;
  busy: boolean;
};

export function ResultStoryBand({ snapshot, busy }: ResultStoryBandProps) {
  const view = presentResultStory({ snapshot, busy });
  return (
    <section className="judge-result-story" aria-label="Result story">
      <ResultStory view={view} />
    </section>
  );
}
