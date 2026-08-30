import { SignalProvenanceError } from "./banner";
import {
  A_REQUIRED_WHEN_COMPUTED,
  B_FORBIDDEN_FIELDS,
  B_REQUIRED_WHEN_PATH_KNOWN,
  NATIONAL_AGGREGATION_SPEC,
  PHOENIX_AGGREGATION_SPEC,
  type PublicSignalProvenance,
  type SignalKind,
} from "./types";

export function publicBDump(
  view: PublicSignalProvenance,
): Record<string, unknown> {
  const dumped: Record<string, unknown> = { ...view };
  delete dumped.reference_version;
  delete dumped.reference_source;
  return dumped;
}

export function assertBHasNoReference(view: PublicSignalProvenance): void {
  if (view.signal_kind !== "selected_time_snapshot") {
    return;
  }
  if (view.reference_version != null || view.reference_source != null) {
    throw new SignalProvenanceError(
      "Signal B provenance cannot carry a historical reference",
    );
  }
  const dumped = publicBDump(view);
  for (const field of B_FORBIDDEN_FIELDS) {
    if (field in dumped && dumped[field] != null) {
      throw new SignalProvenanceError(`Signal B leaked ${field}`);
    }
  }
}

export function missingRequired(
  view: PublicSignalProvenance,
  required: readonly string[],
): string[] {
  return required.filter((name) => {
    const value = view[name as keyof PublicSignalProvenance];
    return value == null || value === "";
  });
}

export function assertAbFieldGuarantees(input: {
  historical?: PublicSignalProvenance | null;
  selectedTime?: PublicSignalProvenance | null;
  aComputed?: boolean;
  bPathKnown?: boolean;
  selectedTimeRequested?: boolean;
  nationalAreaId?: string | null;
}): void {
  const historical = input.historical ?? null;
  const selectedTime = input.selectedTime ?? null;
  if (historical && historical.signal_kind !== "historical_normalized") {
    throw new SignalProvenanceError("historical view must be historical_normalized");
  }
  if (input.aComputed && historical) {
    const missing = missingRequired(historical, A_REQUIRED_WHEN_COMPUTED);
    if (missing.length > 0) {
      throw new SignalProvenanceError(
        `Signal A computed provenance missing required fields: ${missing.join(",")}`,
      );
    }
  }
  if (selectedTime) {
    if (selectedTime.signal_kind !== "selected_time_snapshot") {
      throw new SignalProvenanceError("selected_time view must be selected_time_snapshot");
    }
    assertBHasNoReference(selectedTime);
    if (input.bPathKnown) {
      const missing = missingRequired(selectedTime, B_REQUIRED_WHEN_PATH_KNOWN);
      if (missing.length > 0) {
        throw new SignalProvenanceError(
          `Signal B path-known provenance missing required fields: ${missing.join(",")}`,
        );
      }
    }
    if (input.nationalAreaId?.startsWith("us-place-")) {
      const geometry = selectedTime.geometry_version ?? "";
      if (geometry.includes("PHX_DEMO_AOI") || geometry.includes("PHX_ZTSI_REF")) {
        throw new SignalProvenanceError(
          "national B cannot inherit Phoenix A geometry or reference stamps",
        );
      }
      if (selectedTime.aggregation_spec_version === PHOENIX_AGGREGATION_SPEC) {
        throw new SignalProvenanceError("national B cannot use the Phoenix aggregation id");
      }
      if (
        selectedTime.aggregation_spec_version != null &&
        selectedTime.aggregation_spec_version !== NATIONAL_AGGREGATION_SPEC
      ) {
        throw new SignalProvenanceError(
          "national B aggregation_spec_version must be the national id",
        );
      }
    }
  }
  if (
    historical?.request_fingerprint &&
    selectedTime?.request_fingerprint &&
    historical.request_fingerprint === selectedTime.request_fingerprint
  ) {
    throw new SignalProvenanceError(
      "A and B request fingerprints must not be the same digest",
    );
  }
}

export function activeSignalKind(
  active: SignalKind,
  historical: PublicSignalProvenance | null | undefined,
  selectedTime: PublicSignalProvenance | null | undefined,
): PublicSignalProvenance | null {
  if (active === "historical_normalized") {
    return historical ?? null;
  }
  return selectedTime ?? null;
}

export function refuseAreasCatalogAsBProvenance(
  catalogReferenceVersion?: string | null,
): never {
  throw new SignalProvenanceError(
    catalogReferenceVersion
      ? `GET /areas reference_version is not B provenance (${catalogReferenceVersion})`
      : "GET /areas reference_version is not B provenance",
  );
}
