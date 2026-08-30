import { useEffect, useState } from "react";
import type { AnalysisResultStub } from "@/api/analysisJobs";
import { composeSelectedAreaStory, SelectedAreaStoryPanel } from "@/features/selectedAreaStory";
import { AreaContextList } from "./AreaContextList";
import { MAP_MODE_LABEL } from "./copy";
import { fetchAreaContext } from "./fetchContext";
import { MAP_MODES } from "./mapModes";
import { allowedMapModes, presentList } from "./present";
import { isPublicContextEnabled } from "./publicContextGate";
import type { AreaContextDocument, MapMode } from "./types";
import "./areaContext.css";

export type AreaContextBandProps = {
  areaId?: string;
  selectedZoneId?: string | null;
  result?: AnalysisResultStub | null;
  onSelectTract?: (tractId: string) => void;
  contextEnabled?: boolean;
};

export function AreaContextBand({
  areaId = "phoenix-demo",
  selectedZoneId = null,
  result = null,
  onSelectTract,
  contextEnabled = isPublicContextEnabled(),
}: AreaContextBandProps) {
  const [document, setDocument] = useState<AreaContextDocument | null>(null);
  const [mode, setMode] = useState<MapMode>("THERMAL");

  useEffect(() => {
    if (!contextEnabled) {
      setDocument(null);
      return;
    }
    let cancelled = false;
    void fetchAreaContext(areaId, selectedZoneId)
      .then((payload) => {
        if (!cancelled) {
          setDocument(payload);
        }
      })
      .catch(() => {
        if (!cancelled) {
          setDocument(null);
        }
      });
    return () => {
      cancelled = true;
    };
  }, [areaId, selectedZoneId, contextEnabled]);

  if (!contextEnabled || !document) {
    return null;
  }

  const modes = allowedMapModes(document);
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
      <div className="area-context-modes" role="tablist" aria-label="Context map modes">
        {MAP_MODES.filter((item) => modes.includes(item)).map((item) => (
          <button
            key={item}
            type="button"
            role="tab"
            aria-selected={mode === item}
            data-mode={item}
            onClick={() => setMode(item)}
          >
            {MAP_MODE_LABEL[item]}
          </button>
        ))}
      </div>
      {selectedZoneId ? <SelectedAreaStoryPanel story={story} mode={mode} /> : null}
      <AreaContextList
        rows={presentList(document)}
        mode={mode}
        onSelectTract={onSelectTract}
      />
    </section>
  );
}
