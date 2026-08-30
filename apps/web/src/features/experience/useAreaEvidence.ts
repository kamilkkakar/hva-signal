import { useEffect, useState } from "react";
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

  useEffect(() => {
    let cancelled = false;
    if (!selectedZoneId) {
      setMatchedDoc(null);
      setObservedDoc(null);
      setContext(null);
      setMatchedError(null);
      setObservedError(null);
      return;
    }
    const hit = cache.get(selectedZoneId);
    if (hit) {
      setContext(hit.context);
    }
    setMatchedError(null);
    setObservedError(null);
    void retry(() => fetchMatchedNighttimeWindow(selectedZoneId))
      .then((doc) => {
        if (!cancelled) setMatchedDoc(doc);
      })
      .catch((error: unknown) => {
        if (!cancelled) {
          setMatchedDoc(null);
          setMatchedError(error instanceof Error ? error.message : "Unavailable");
        }
      });
    void retry(() => fetchObservedThermalInstants(selectedZoneId))
      .then((doc) => {
        if (!cancelled) setObservedDoc(doc);
      })
      .catch((error: unknown) => {
        if (!cancelled) {
          setObservedDoc(null);
          setObservedError(error instanceof Error ? error.message : "Unavailable");
        }
      });
    void retry(() => fetchAreaContext("phoenix-demo", selectedZoneId))
      .then((doc) => {
        if (!cancelled) setContext(doc);
      })
      .catch(() => {
        if (!cancelled) setContext(null);
      });
    return () => {
      cancelled = true;
    };
  }, [selectedZoneId]);

  const matched = presentMatched(selectedZoneId, matchedDoc, matchedError);
  const observed = presentObserved(selectedZoneId, observedDoc, observedError);
  useEffect(() => {
    if (!selectedZoneId) {
      return;
    }
    if (matched.status === "AVAILABLE" && observed.status === "AVAILABLE") {
      cache.set(selectedZoneId, { matched, observed, context });
    }
  }, [selectedZoneId, matched, observed, context]);
  return { matched, observed, context };
}
