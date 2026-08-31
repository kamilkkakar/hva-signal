import { useEffect, useRef, useState } from "react";
import { fetchAreaContext } from "@/features/areaContext/fetchContext";
import type { AreaContextDocument } from "@/features/areaContext/types";
import { fetchMatchedNighttimeWindow, fetchObservedThermalInstants } from "@/features/judgeShell/decision/fetchStories";
import { presentMatched, presentObserved } from "@/features/judgeShell/decision/present";
import type { MatchedNighttimeView, ObservedSequenceView, PresentedMatched, PresentedSequence } from "@/features/judgeShell/decision/types";

export type AreaEvidence = {
  matched: PresentedMatched;
  observed: PresentedSequence;
  context: AreaContextDocument | null;
};

const cache = new Map<string, AreaEvidence>();

async function retry<T>(run: () => Promise<T>, attempts = 6): Promise<T> {
  let last: unknown;
  for (let index = 0; index < attempts; index += 1) {
    try {
      return await run();
    } catch (error) {
      last = error;
      await new Promise((resolve) => setTimeout(resolve, 400 * (index + 1)));
    }
  }
  throw last instanceof Error ? last : new Error("Unavailable");
}

export function useAreaEvidence(selectedZoneId: string | null): AreaEvidence {
  const [matchedDoc, setMatchedDoc] = useState<MatchedNighttimeView | null>(null);
  const [observedDoc, setObservedDoc] = useState<ObservedSequenceView | null>(null);
  const [context, setContext] = useState<AreaContextDocument | null>(null);
  const [matchedError, setMatchedError] = useState<string | null>(null);
  const [observedError, setObservedError] = useState<string | null>(null);
  const [boundZoneId, setBoundZoneId] = useState<string | null>(selectedZoneId);
  const sequenceRef = useRef(0);

  useEffect(() => {
    const sequence = ++sequenceRef.current;
    let cancelled = false;
    if (!selectedZoneId) {
      setMatchedDoc(null);
      setObservedDoc(null);
      setContext(null);
      setMatchedError(null);
      setObservedError(null);
      setBoundZoneId(null);
      return;
    }
    const hit = cache.get(selectedZoneId);
    if (hit) {
      setMatchedDoc(null);
      setObservedDoc(null);
      setContext(hit.context);
      setMatchedError(null);
      setObservedError(null);
      setBoundZoneId(selectedZoneId);
      // Restore presented cache atomically via docs by re-presenting through state below.
      // matched/observed docs are zone-bound; apply cached views through a sync path:
      setContext(hit.context);
    } else {
      // Drop prior-area payloads immediately so UI cannot mix area A metrics under label B.
      setMatchedDoc(null);
      setObservedDoc(null);
      setContext(null);
      setBoundZoneId(selectedZoneId);
    }
    setMatchedError(null);
    setObservedError(null);

    const stillCurrent = () => !cancelled && sequenceRef.current === sequence;

    void retry(() => fetchMatchedNighttimeWindow(selectedZoneId))
      .then((doc) => {
        if (stillCurrent()) setMatchedDoc(doc);
      })
      .catch((error: unknown) => {
        if (stillCurrent()) {
          setMatchedDoc(null);
          setMatchedError(error instanceof Error ? error.message : "Unavailable");
        }
      });
    void retry(() => fetchObservedThermalInstants(selectedZoneId))
      .then((doc) => {
        if (stillCurrent()) setObservedDoc(doc);
      })
      .catch((error: unknown) => {
        if (stillCurrent()) {
          setObservedDoc(null);
          setObservedError(error instanceof Error ? error.message : "Unavailable");
        }
      });
    void retry(() => fetchAreaContext("phoenix-demo", selectedZoneId))
      .then((doc) => {
        if (stillCurrent()) setContext(doc);
      })
      .catch(() => {
        if (stillCurrent()) setContext(null);
      });
    return () => {
      cancelled = true;
    };
  }, [selectedZoneId]);

  // Present only when docs belong to the currently selected zone (stale-response safety).
  const activeZoneId = boundZoneId === selectedZoneId ? selectedZoneId : null;
  const matched = presentMatched(activeZoneId, matchedDoc, matchedError);
  const observed = presentObserved(activeZoneId, observedDoc, observedError);
  useEffect(() => {
    if (!selectedZoneId || boundZoneId !== selectedZoneId) {
      return;
    }
    if (matched.status === "AVAILABLE" && observed.status === "AVAILABLE") {
      cache.set(selectedZoneId, { matched, observed, context });
    }
  }, [selectedZoneId, boundZoneId, matched, observed, context]);

  // Prefer fully cached coherent evidence when present to avoid loading flicker on revisit.
  const cached = selectedZoneId ? cache.get(selectedZoneId) : undefined;
  if (
    cached &&
    selectedZoneId &&
    boundZoneId === selectedZoneId &&
    matched.status !== "AVAILABLE" &&
    observed.status !== "AVAILABLE"
  ) {
    return cached;
  }
  return { matched, observed, context };
}
