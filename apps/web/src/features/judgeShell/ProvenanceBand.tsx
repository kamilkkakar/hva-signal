import type { AnalysisJobPayload } from "@/api/analysisJobs";
import {
  CommandCenterProvenanceHeader,
  HowDetermined,
  PublicProvenanceExperience,
  bindProvenanceFromJob,
} from "@/features/provenance";
import { Decision8AccordionView } from "./results";

type ProvenanceBandProps = {
  snapshot: AnalysisJobPayload | null;
};

export function ProvenanceBand({ snapshot }: ProvenanceBandProps) {
  const bound = bindProvenanceFromJob({ job: snapshot });

  return (
    <section className="judge-provenance" aria-label="Provenance">
      <HowDetermined snapshot={snapshot} />
      <CommandCenterProvenanceHeader job={snapshot} />
      <PublicProvenanceExperience
        historical={bound.historical}
        selectedTime={bound.selectedTime}
        historicalRequested={bound.historicalRequested}
        selectedTimeRequested={bound.selectedTimeRequested}
        historicalCoverage={bound.historicalCoverage}
        selectedTimeCoverage={bound.selectedTimeCoverage}
        historicalAreaId={bound.historicalAreaId}
        selectedTimeAreaId={bound.selectedTimeAreaId}
        historicalLevel2Extras={bound.historicalLevel2Extras}
        selectedTimeLevel2Extras={bound.selectedTimeLevel2Extras}
      />
      <aside role="complementary" aria-label="Decision panel">
        <Decision8AccordionView snapshot={snapshot} />
      </aside>
    </section>
  );
}
