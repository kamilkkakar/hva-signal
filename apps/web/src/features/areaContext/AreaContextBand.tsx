import { useEffect, useState } from "react";
import type { AnalysisResultStub } from "@/api/analysisJobs";
import { AreaContextList } from "./AreaContextList";
import { SELECT_AREA_PROMPT } from "./copy";
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
  result: _result = null,
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
    void (async () => {
      for (let attempt = 0; attempt < 6 && !cancelled; attempt += 1) {
        try {
          const payload = await fetchAreaContext(areaId, selectedZoneId);
          if (!cancelled) {
            setDocument(payload);
            onContextZones?.(payload.zones);
          }
          return;
        } catch {
          await new Promise((resolve) => setTimeout(resolve, 400 * (attempt + 1)));
        }
      }
      if (!cancelled) {
        setDocument(null);
        onContextZones?.([]);
      }
    })();
    return () => {
      cancelled = true;
    };
  }, [areaId, selectedZoneId, contextEnabled, onContextZones]);

  if (!contextEnabled || !document) {
    return null;
  }

  return (
    <section
      className="judge-area-context"
      data-testid="area-context-band"
      aria-label="Analysis area context"
    >
      {!selectedZoneId ? (
        <p data-testid="area-context-select-prompt">{SELECT_AREA_PROMPT}</p>
      ) : null}
      <AreaContextList
        rows={presentList(document)}
        mode={mapMode}
        selectedZoneId={selectedZoneId}
        onSelectTract={onSelectTract}
      />
    </section>
  );
}
