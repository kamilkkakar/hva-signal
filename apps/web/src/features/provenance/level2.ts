import { signalProvenanceBanner, SignalProvenanceError } from "./banner";
import { assertBHasNoReference } from "./fieldGuarantees";
import type { PublicSignalProvenance } from "./types";

export type Level2RowKind = "version" | "hash" | "text";

export type Level2Row = {
  key: string;
  label: string;
  value: string;
  kind: Level2RowKind;
};

export type Level2Extras = {
  area_config_sha256?: string | null;
  reference_source_sha256?: string | null;
};

function pushRow(
  rows: Level2Row[],
  key: string,
  label: string,
  value: string | null | undefined,
  kind: Level2RowKind,
): void {
  if (value == null || value === "") {
    return;
  }
  rows.push({ key, label, value, kind });
}

export function projectLevel2(
  view: PublicSignalProvenance,
  extras: Level2Extras = {},
): Level2Row[] {
  if (view.signal_kind === "selected_time_snapshot") {
    assertBHasNoReference(view);
  }

  const rows: Level2Row[] = [];
  const { banner, pathStem } = signalProvenanceBanner({
    source: view.source,
    dataStatus: view.data_status,
  });
  const bannerText =
    banner === "PARTIAL" && pathStem != null ? `${banner} · ${pathStem}` : banner;
  pushRow(rows, "contract_banner", "Contract banner", bannerText, "text");
  pushRow(rows, "geometry_version", "Geometry policy", view.geometry_version, "version");
  pushRow(
    rows,
    "aggregation_spec_version",
    "Aggregation",
    view.aggregation_spec_version,
    "version",
  );

  if (view.signal_kind === "historical_normalized") {
    pushRow(rows, "reference_version", "Historical reference", view.reference_version, "version");
    pushRow(rows, "reference_source", "Reference source", view.reference_source, "text");
    pushRow(
      rows,
      "reference_source_sha256",
      "Reference hash",
      extras.reference_source_sha256,
      "hash",
    );
  }

  pushRow(rows, "geometry_sha256", "Geometry hash", view.geometry_sha256, "hash");
  pushRow(rows, "area_config_sha256", "Area config hash", extras.area_config_sha256, "hash");
  pushRow(rows, "request_fingerprint", "Request fingerprint", view.request_fingerprint, "hash");

  if (view.signal_kind === "selected_time_snapshot") {
    for (const row of rows) {
      if (row.key.includes("reference") || row.label.toLowerCase().includes("reference")) {
        throw new SignalProvenanceError("Signal B Level 2 leaked a reference row");
      }
    }
  }

  return rows;
}
