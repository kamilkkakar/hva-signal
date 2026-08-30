import { useEffect, useState } from "react";
import { analysisAreaLabel } from "@/features/selectedAreaStory/identity";
import { EvidenceLedger } from "./EvidenceLedger";
import { fetchMatchedNighttimeWindow, fetchObservedThermalInstants } from "./fetchStories";
import { InterventionVerifyCopy } from "./InterventionVerifyCopy";
import { MatchedNighttimePanel } from "./MatchedNighttimePanel";
import { ObservedInstantsChart } from "./ObservedInstantsChart";
import { presentMatched, presentObserved } from "./present";
import { QuestionNav } from "./QuestionNav";
import { PRODUCT_QUESTIONS, type ProductQuestionId } from "./questions";
import type { MatchedNighttimeView, ObservedSequenceView } from "./types";
import "./decision.css";

type DecisionStoriesBandProps = {
  selectedZoneId?: string | null;
  fetchImpl?: typeof fetch;
};

export function DecisionStoriesBand({
  selectedZoneId = null,
  fetchImpl = fetch,
}: DecisionStoriesBandProps) {
  const [activeId, setActiveId] = useState<ProductQuestionId>("matched-nighttime");
  const [matchedDoc, setMatchedDoc] = useState<MatchedNighttimeView | null>(null);
  const [observedDoc, setObservedDoc] = useState<ObservedSequenceView | null>(null);
  const [matchedError, setMatchedError] = useState<string | null>(null);
  const [observedError, setObservedError] = useState<string | null>(null);

  useEffect(() => {
    let cancelled = false;
    if (!selectedZoneId) {
      setMatchedDoc(null);
      setObservedDoc(null);
      setMatchedError(null);
      setObservedError(null);
      return;
    }
    setMatchedError(null);
    setObservedError(null);
    void fetchMatchedNighttimeWindow(selectedZoneId, fetchImpl)
      .then((doc) => {
        if (!cancelled) setMatchedDoc(doc);
      })
      .catch((error: unknown) => {
        if (!cancelled) {
          setMatchedDoc(null);
          setMatchedError(error instanceof Error ? error.message : "Unavailable");
        }
      });
    void fetchObservedThermalInstants(selectedZoneId, fetchImpl)
      .then((doc) => {
        if (!cancelled) setObservedDoc(doc);
      })
      .catch((error: unknown) => {
        if (!cancelled) {
          setObservedDoc(null);
          setObservedError(error instanceof Error ? error.message : "Unavailable");
        }
      });
    return () => {
      cancelled = true;
    };
  }, [selectedZoneId, fetchImpl]);

  const matched = presentMatched(selectedZoneId, matchedDoc, matchedError);
  const observed = presentObserved(selectedZoneId, observedDoc, observedError);
  const area = analysisAreaLabel(selectedZoneId);

  function selectQuestion(id: ProductQuestionId) {
    setActiveId(id);
    const target = PRODUCT_QUESTIONS.find((question) => question.id === id)?.target;
    if (!target) return;
    document.getElementById(target)?.scrollIntoView({ block: "start" });
  }

  return (
    <section
      className="judge-decision"
      data-testid="decision-stories"
      aria-label="Decision stories"
    >
      <p className="kicker">Decision</p>
      <h2>{area ?? "Select an analysis area"}</h2>
      <QuestionNav activeId={activeId} onSelect={selectQuestion} />
      <EvidenceLedger geoid={selectedZoneId} matched={matched} />
      <div id="matched-nighttime">
        <MatchedNighttimePanel view={matched} />
      </div>
      <div id="observed-times">
        <ObservedInstantsChart view={observed} />
      </div>
      <div id="verify-before-action">
        <InterventionVerifyCopy />
      </div>
    </section>
  );
}
