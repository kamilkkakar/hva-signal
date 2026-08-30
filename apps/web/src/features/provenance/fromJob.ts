import { signalProvenanceBanner, SignalProvenanceError } from "./banner";
import { assertAbFieldGuarantees, assertBHasNoReference } from "./fieldGuarantees";
import { ANALYSIS_ZONE_COUNT, type CoverageCount } from "./level1";
import type { Level2Extras } from "./level2";
import { legacyThermalSource } from "./rail";
import type {
  ProvenanceDataStatus,
  ProvenanceSource,
  PublicSignalProvenance,
} from "./types";

export type JobBindZone = {
  zone_id?: string;
  thermal_observation_valid?: boolean;
  coverage_status?: "valid" | "missing";
};

export type JobBindInput = {
  status?: string | null;
  request?: {
    area_id?: string;
    analysis_time?: string;
    data_mode?: string;
  } | null;
  result?: {
    data_status?: string | null;
    thermal_source?: string | null;
    zones?: JobBindZone[];
    versions?: {
      zone_geometry_version?: string;
      thermal_aggregation_version?: string;
      area_config_version?: string;
    } | null;
    hazard_spread?: {
      reference_version?: string | null;
      zone_geometry_version?: string | null;
    } | null;
    area_config_sha256?: string | null;
    reference_source_sha256?: string | null;
  } | null;
};

export type SelectedTimeBindSection = {
  requested?: boolean;
  provenance?: PublicSignalProvenance | null;
  provenance_source?: string | null;
  data_status?: string | null;
  target_timestamp?: string | null;
  timezone?: string | null;
  valid_zone_count?: number | null;
  expected_zone_count?: number;
  geometry_version?: string | null;
  geometry_sha256?: string | null;
  aggregation_spec_version?: string | null;
  reference_version?: unknown;
  reference_source?: unknown;
};

export type FromJobInput = {
  job?: JobBindInput | null;
  historical?: PublicSignalProvenance | null;
  selectedTime?: PublicSignalProvenance | null;
  historicalRequested?: boolean;
  selectedTimeRequested?: boolean;
  historicalCoverage?: CoverageCount | null;
  selectedTimeCoverage?: CoverageCount | null;
  selectedTimeSection?: SelectedTimeBindSection | null;
};

export type BoundProvenance = {
  historical: PublicSignalProvenance | null;
  selectedTime: PublicSignalProvenance | null;
  historicalRequested: boolean;
  selectedTimeRequested: boolean;
  historicalCoverage: CoverageCount | null;
  selectedTimeCoverage: CoverageCount | null;
  historicalAreaId: string | null;
  selectedTimeAreaId: string | null;
  historicalLevel2Extras: Level2Extras;
  selectedTimeLevel2Extras: Level2Extras;
  legacyThermalSource: string | null;
  collapsed: false;
};

export function asProvenanceSource(value: string | null | undefined): ProvenanceSource | null {
  if (value === "replay" || value === "fortyguard_cached" || value === "fortyguard_live") {
    return value;
  }
  return null;
}

export function asProvenanceStatus(
  value: string | null | undefined,
): ProvenanceDataStatus | null {
  if (
    value === "live" ||
    value === "cached" ||
    value === "replay" ||
    value === "partial" ||
    value === "unavailable"
  ) {
    return value;
  }
  return null;
}

export function coverageFromZones(
  zones: readonly JobBindZone[] | null | undefined,
  expected = ANALYSIS_ZONE_COUNT,
): CoverageCount | null {
  if (zones == null) {
    return null;
  }
  let valid = 0;
  let sawValidity = false;
  for (const zone of zones) {
    if (zone.coverage_status === "valid") {
      sawValidity = true;
      valid += 1;
    } else if (zone.coverage_status === "missing") {
      sawValidity = true;
    } else if (zone.thermal_observation_valid === true) {
      sawValidity = true;
      valid += 1;
    } else if (zone.thermal_observation_valid === false) {
      sawValidity = true;
    }
  }
  if (sawValidity) {
    return { valid, expected };
  }
  return { valid: zones.length, expected };
}

export function aTargetTimestamp(analysisTime: string | null | undefined): string | null {
  if (!analysisTime) {
    return null;
  }
  const date = analysisTime.slice(0, 10);
  if (!/^\d{4}-\d{2}-\d{2}$/.test(date)) {
    return null;
  }
  return `${date}T03:00:00`;
}

function aOnlySourcePair(result: NonNullable<JobBindInput["result"]>): {
  source: ProvenanceSource | null;
  dataStatus: ProvenanceDataStatus | null;
} {
  const dataStatus = asProvenanceStatus(result.data_status);
  const thermal = asProvenanceSource(result.thermal_source);

  if (thermal && dataStatus) {
    signalProvenanceBanner({ source: thermal, dataStatus });
    return { source: thermal, dataStatus };
  }
  if (dataStatus === "replay" && thermal == null) {
    return { source: "replay", dataStatus: "replay" };
  }
  if (dataStatus === "cached" && thermal == null) {
    return { source: "fortyguard_cached", dataStatus: "cached" };
  }
  if (dataStatus === "live" && thermal == null) {
    return { source: "fortyguard_live", dataStatus: "live" };
  }
  if (thermal && dataStatus == null) {
    const inferred: ProvenanceDataStatus =
      thermal === "replay" ? "replay" : thermal === "fortyguard_cached" ? "cached" : "live";
    signalProvenanceBanner({ source: thermal, dataStatus: inferred });
    return { source: thermal, dataStatus: inferred };
  }
  return { source: thermal, dataStatus };
}

function historicalFromAOnlyJob(job: JobBindInput): PublicSignalProvenance | null {
  const result = job.result;
  const request = job.request;
  if (result == null && request == null) {
    return null;
  }
  const pair = result
    ? aOnlySourcePair(result)
    : { source: null as ProvenanceSource | null, dataStatus: null as ProvenanceDataStatus | null };
  const areaId = request?.area_id ?? "";
  const referenceVersion = result?.hazard_spread?.reference_version ?? null;
  return {
    signal_kind: "historical_normalized",
    source: pair.source,
    data_status: pair.dataStatus,
    target_timestamp: aTargetTimestamp(request?.analysis_time),
    timezone: areaId === "phoenix-demo" ? "America/Phoenix" : null,
    geometry_version:
      result?.versions?.zone_geometry_version ??
      result?.hazard_spread?.zone_geometry_version ??
      null,
    aggregation_spec_version: result?.versions?.thermal_aggregation_version ?? null,
    reference_version: referenceVersion,
    reference_source: referenceVersion != null ? "cached_reference" : null,
    availability: referenceVersion == null && result == null ? "NOT_PREPARED" : null,
  };
}

export function selectedTimeFromSection(
  section: SelectedTimeBindSection,
): PublicSignalProvenance {
  if (section.reference_version != null || section.reference_source != null) {
    throw new SignalProvenanceError("Signal B provenance cannot carry a historical reference");
  }
  if (section.provenance) {
    if (section.provenance.signal_kind !== "selected_time_snapshot") {
      throw new SignalProvenanceError("selected_time view must be selected_time_snapshot");
    }
    assertBHasNoReference(section.provenance);
    return section.provenance;
  }
  const view: PublicSignalProvenance = {
    signal_kind: "selected_time_snapshot",
    source: asProvenanceSource(section.provenance_source),
    data_status: asProvenanceStatus(section.data_status),
    target_timestamp: section.target_timestamp ?? null,
    timezone: section.timezone ?? null,
    geometry_version: section.geometry_version ?? null,
    geometry_sha256: section.geometry_sha256 ?? null,
    aggregation_spec_version: section.aggregation_spec_version ?? null,
  };
  assertBHasNoReference(view);
  return view;
}

export function bindProvenanceFromJob(input: FromJobInput): BoundProvenance {
  const job = input.job ?? null;
  const section = input.selectedTimeSection ?? null;
  const selectedTimeRequested =
    input.selectedTimeRequested ??
    (section?.requested === true || input.selectedTime != null);
  const historicalRequested = input.historicalRequested ?? true;

  const historical =
    input.historical ?? (job != null ? historicalFromAOnlyJob(job) : null);

  let selectedTime = input.selectedTime ?? null;
  if (selectedTime == null && section != null && (section.requested || selectedTimeRequested)) {
    selectedTime = selectedTimeFromSection(section);
  }
  if (selectedTimeRequested && selectedTime == null) {
    selectedTime = {
      signal_kind: "selected_time_snapshot",
      source: null,
      data_status: "unavailable",
    };
  }

  if (selectedTime) {
    assertBHasNoReference(selectedTime);
  }

  assertAbFieldGuarantees({
    historical,
    selectedTime,
    selectedTimeRequested,
    nationalAreaId: job?.request?.area_id ?? null,
  });

  const historicalCoverage =
    input.historicalCoverage ?? coverageFromZones(job?.result?.zones ?? null);
  const selectedTimeCoverage =
    input.selectedTimeCoverage ??
    (section?.valid_zone_count != null
      ? {
          valid: section.valid_zone_count,
          expected: section.expected_zone_count ?? ANALYSIS_ZONE_COUNT,
        }
      : null);

  return {
    historical,
    selectedTime,
    historicalRequested,
    selectedTimeRequested,
    historicalCoverage,
    selectedTimeCoverage,
    historicalAreaId: job?.request?.area_id ?? null,
    selectedTimeAreaId: job?.request?.area_id ?? null,
    historicalLevel2Extras: {
      area_config_sha256: job?.result?.area_config_sha256 ?? null,
      reference_source_sha256: job?.result?.reference_source_sha256 ?? null,
    },
    selectedTimeLevel2Extras: {},
    legacyThermalSource: legacyThermalSource({
      selectedTimeRequested,
      historicalSource: historical?.source,
    }),
    collapsed: false,
  };
}
