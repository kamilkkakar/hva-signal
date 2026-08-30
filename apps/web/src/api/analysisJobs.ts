import type { DataMode, JobStatus, ThermalDataSource } from "@/types";
import { apiUrl } from "./baseUrl";

export const HORIZON_MIN = 0;
export const HORIZON_MAX = 12;
export const GRANULARITIES = [60, 80, 100] as const;
export const LOOKBACK_MAX = 24 * 31;

export type GranularityM = (typeof GRANULARITIES)[number];

export type AnalysisJobRequest = {
  area_id: string;
  analysis_time: string;
  analysis_mode: "operational" | "retrospective";
  horizon_hours: number;
  lookback_hours: number;
  granularity_m: GranularityM;
  data_mode: DataMode;
};

export type AnalysisJobDraft = {
  area_id: string;
  analysis_time: string;
  analysis_mode: "operational" | "retrospective";
  horizon_hours: number;
  lookback_hours?: number;
  granularity_m: number;
  data_mode?: DataMode;
};

export type ProbabilityStub = {
  status?: string;
  value?: unknown;
};

export type EvidenceGraphStub = {
  nodes?: unknown;
  edges?: unknown;
};

export type ZoneDecisionStub = {
  zone_id: string;
  ranked?: boolean;
  probability?: ProbabilityStub | null;
  thermal_ordering_permitted?: boolean;
  q_A?: number | null;
};

export type AnalysisResultStub = {
  data_status?: string;
  thermal_source?: ThermalDataSource;
  system_limitations?: string[];
  limitations?: string[];
  zones?: ZoneDecisionStub[];
  evidence_graph?: EvidenceGraphStub | null;
  reference_quality?: string | null;
  thermal_differentiation_state?: string | null;
  versions?: {
    area_config_version?: string;
    zone_geometry_version?: string;
    hazard_spread_policy_version?: string;
  } | null;
  area_config_sha256?: string | null;
  reference_source_sha256?: string | null;
  hazard_spread?: {
    policy_version?: string;
    reference_version?: string | null;
    zone_geometry_version?: string | null;
    input_quantity?: string | null;
    metric?: string;
    top_group_size?: number | null;
    bottom_group_size?: number | null;
    floor?: number | null;
    comparison_operator?: string | null;
    observed_spread?: number | null;
    differentiation_state?: string;
    reference_quality?: string;
    suppression_reason?: string | null;
    historical_years?: number[] | null;
    reference_hour?: string | null;
  } | null;
};

export type AnalysisJobPayload = {
  job_id: string;
  status: JobStatus;
  request?: AnalysisJobRequest;
  created_at?: string;
  recoverable?: boolean;
  message?: string | null;
  result?: AnalysisResultStub | null;
};

function isGranularity(value: number): value is GranularityM {
  return (GRANULARITIES as readonly number[]).includes(value);
}

export function buildAnalysisJobRequest(draft: AnalysisJobDraft): AnalysisJobRequest {
  const areaId = draft.area_id.trim();
  if (!areaId) {
    throw new Error("Area is required.");
  }
  if (draft.horizon_hours < HORIZON_MIN || draft.horizon_hours > HORIZON_MAX) {
    throw new Error("Horizon must be 0–12 hours.");
  }
  if (!isGranularity(draft.granularity_m)) {
    throw new Error("Granularity must be 60, 80, or 100 meters.");
  }
  const lookbackHours = draft.lookback_hours ?? 0;
  if (lookbackHours < 0 || lookbackHours > LOOKBACK_MAX) {
    throw new Error("Lookback must be 0–744 hours.");
  }
  if (!draft.analysis_time) {
    throw new Error("Analysis time is required.");
  }

  return {
    area_id: areaId,
    analysis_time: draft.analysis_time,
    analysis_mode: draft.analysis_mode,
    horizon_hours: draft.horizon_hours,
    lookback_hours: lookbackHours,
    granularity_m: draft.granularity_m,
    data_mode: draft.data_mode ?? "replay",
  };
}

async function readJson(response: Response): Promise<AnalysisJobPayload> {
  return (await response.json()) as AnalysisJobPayload;
}

export async function createAnalysisJob(
  request: AnalysisJobRequest,
  fetchImpl: typeof fetch = fetch,
): Promise<AnalysisJobPayload> {
  const response = await fetchImpl(apiUrl("/api/v1/analysis/jobs"), {
    method: "POST",
    headers: {
      Accept: "application/json",
      "Content-Type": "application/json",
    },
    body: JSON.stringify(request),
  });
  if (!response.ok) {
    throw new Error(`Analysis job was rejected (${response.status}).`);
  }
  return readJson(response);
}

export async function getAnalysisJob(
  jobId: string,
  fetchImpl: typeof fetch = fetch,
): Promise<AnalysisJobPayload> {
  const response = await fetchImpl(apiUrl(`/api/v1/analysis/jobs/${jobId}`), {
    method: "GET",
    headers: { Accept: "application/json" },
  });
  if (!response.ok) {
    throw new Error(`Could not read analysis job (${response.status}).`);
  }
  return readJson(response);
}
