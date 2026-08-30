import { signalBFillPaint, signalBLinePaint } from "./signalBFill";
import { bindSignalBGeometry } from "./signalBGeometry";
import { signalBMapIsEnabled } from "./signalBMapGate";
import {
  SIGNAL_B_LAYER_TITLE,
  SIGNAL_B_MEANING_COPY,
  SIGNAL_B_METHODOLOGY_COPY,
  SIGNAL_B_STRETCH_COPY,
  SIGNAL_B_UNAVAILABLE_COPY,
  snapshotFactsText,
} from "./signalBPolicy";
import { signalBTableRows } from "./signalBTable";
import type {
  SignalBBoundCollection,
  SignalBGeometryCollection,
  SignalBMapAvailability,
  SignalBMapPresentation,
  SignalBMapVisualState,
  SignalBSnapshot,
  SignalBSnapshotFacts,
} from "./signalBTypes";

const EMPTY_COLLECTION: SignalBBoundCollection = {
  type: "FeatureCollection",
  features: [],
};

function factsFromSnapshot(snapshot: SignalBSnapshot | null): SignalBSnapshotFacts {
  if (!snapshot) {
    return { temperature_min_c: null, temperature_max_c: null, factText: null };
  }
  let minC = snapshot.temperature_min_c ?? null;
  let maxC = snapshot.temperature_max_c ?? null;
  if (minC == null || maxC == null) {
    const values = snapshot.zones
      .map((zone) => zone.mean_temperature_c)
      .filter((value): value is number => value != null && Number.isFinite(value));
    if (values.length > 0) {
      minC = Math.min(...values);
      maxC = Math.max(...values);
    }
  }
  return {
    temperature_min_c: minC,
    temperature_max_c: maxC,
    factText: snapshotFactsText(minC, maxC),
  };
}

function emptyPresentation(
  visualState: SignalBMapVisualState,
  message: string | null,
  snapshot: SignalBSnapshot | null = null,
): SignalBMapPresentation {
  return {
    layerTitle: SIGNAL_B_LAYER_TITLE,
    visualState,
    fillPaint: signalBFillPaint(),
    linePaint: signalBLinePaint(),
    collection: EMPTY_COLLECTION,
    tableRows: snapshot ? signalBTableRows({ snapshot }) : [],
    snapshotFacts: factsFromSnapshot(snapshot),
    autoContrastBanner: null,
    meaningCopy: SIGNAL_B_MEANING_COPY,
    methodologyCopy: SIGNAL_B_METHODOLOGY_COPY,
    stretchCopy: SIGNAL_B_STRETCH_COPY,
    message,
    outlineCount: 0,
    validFillCount: 0,
  };
}

function visualFromAvailability(
  availability: SignalBMapAvailability | undefined,
  missingTemperatureCount: number,
): SignalBMapVisualState {
  if (availability === "fetching") {
    return "loading";
  }
  if (availability === "unavailable") {
    return "unavailable";
  }
  if (availability === "idle") {
    return "idle";
  }
  if (availability === "partial" || missingTemperatureCount > 0) {
    return "partial";
  }
  return "ready";
}

export function presentSignalBMap(input: {
  enabled?: boolean;
  snapshot: SignalBSnapshot | null;
  geometry: SignalBGeometryCollection | null;
  availability?: SignalBMapAvailability;
}): SignalBMapPresentation {
  if (!signalBMapIsEnabled(input.enabled)) {
    return emptyPresentation("gated_off", null);
  }
  if (input.availability === "fetching") {
    return emptyPresentation("loading", "Loading selected-time snapshot geometry.");
  }
  if (input.availability === "unavailable") {
    return emptyPresentation("unavailable", SIGNAL_B_UNAVAILABLE_COPY);
  }
  if (!input.snapshot || !input.geometry) {
    if (input.availability === "ready" || input.availability === "partial") {
      return emptyPresentation(
        "error",
        "Selected-time snapshot geometry is not available.",
        input.snapshot,
      );
    }
    return emptyPresentation("idle", null, input.snapshot);
  }
  const bound = bindSignalBGeometry({
    geometry: input.geometry,
    snapshot: input.snapshot,
  });
  if (!bound.ok) {
    return emptyPresentation("error", bound.reason, input.snapshot);
  }
  const visualState = visualFromAvailability(
    input.availability,
    bound.missingTemperatureCount,
  );
  return {
    layerTitle: SIGNAL_B_LAYER_TITLE,
    visualState,
    fillPaint: signalBFillPaint(),
    linePaint: signalBLinePaint(),
    collection: bound.collection,
    tableRows: signalBTableRows({
      snapshot: input.snapshot,
      boundFeatures: bound.collection.features,
    }),
    snapshotFacts: factsFromSnapshot(input.snapshot),
    autoContrastBanner: null,
    meaningCopy: SIGNAL_B_MEANING_COPY,
    methodologyCopy: SIGNAL_B_METHODOLOGY_COPY,
    stretchCopy: SIGNAL_B_STRETCH_COPY,
    message:
      visualState === "partial"
        ? "Signal B is partial. Zones without a value are unknown. Partial coverage is not filled as complete."
        : null,
    outlineCount: bound.joinedCount,
    validFillCount: bound.joinedCount - bound.missingTemperatureCount,
  };
}
