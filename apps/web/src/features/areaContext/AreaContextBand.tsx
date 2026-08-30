import { useEffect, useState } from "react";
import type { AnalysisResultStub } from "@/api/analysisJobs";
import { composeSelectedAreaStory, SelectedAreaStoryPanel } from "@/features/selectedAreaStory";
import { AreaContextList } from "./AreaContextList";
import { fetchAreaContext } from "./fetchContext";
import { presentList } from "./present";
import { isPublicContextEnabled } from "./publicContextGate";
import type { AreaContextDocument, MapMode, ZoneMapProperties } from "./types";
import "./areaContext.css";

export type AreaContextBandProps = {
  areaId?: string;
  selectedZoneId?: string | null;
  result?: AnalysisResultStub | null;
  mapMode?: MapMode;
  onSelectTract?: (tractId: string) => void;
  onContextZones?: (zones: ZoneMapProperties[]) => void;
  contextEnabled?: boolean;
};

export function AreaContextBand({
  areaId = "phoenix-demo",
  selectedZoneId = null,
  result = null,
  mapMode = "THERMAL",
  onSelectTract,
  onContextZones,
  contextEnabled = isPublicContextEnabled(),
}: AreaContextBandProps) {
  const [document, setDocument] = useState<AreaContextDocument | null>(null);

  useEffect(() => {
    if (!contextEnabled) {
      setDocument(null);
      onContextZones?.([]);
      return;
    }
    let cancelled = false;
    void fetchAreaContext(areaId, selectedZoneId)
      .then((payload) => {
        if (cancelled) {
          return;
        }
        setDocument(payload);
        onContextZones?.(payload.zones);
      })
      .catch(() => {
        if (!cancelled) {
          setDocument(null);
          onContextZones?.([]);
        }
      });
    return () => {
      cancelled = true;
    };
  }, [areaId, selectedZoneId, contextEnabled, onContextZones]);

  if (!contextEnabled || !document) {
    return null;
  }

  const story = composeSelectedAreaStory({
    selectedGeoid: selectedZoneId,
    result,
    context: document.selected,
    document,
  });

  return (
    <section
      className="judge-area-context"
      data-testid="area-context-band"
      aria-label="Analysis area context"
    >
      {selectedZoneId ? <SelectedAreaStoryPanel story={story} mode={mapMode} /> : null}
      <AreaContextList
        rows={presentList(document)}
        mode={mapMode}
        selectedZoneId={selectedZoneId}
        onSelectTract={onSelectTract}
      />
    </section>
  );
}
