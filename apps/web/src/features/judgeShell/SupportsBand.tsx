import type { AnalysisResultStub } from "@/api/analysisJobs";
import type { JobStatus } from "@/types";
import { ActionSupportsBand } from "./action";

type SupportsBandProps = {
  status: JobStatus | null;
  result: AnalysisResultStub | null;
};

export function SupportsBand({ status, result }: SupportsBandProps) {
  return <ActionSupportsBand status={status} result={result} />;
}
