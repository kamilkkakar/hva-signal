import { ANALYSIS_AREAS, publicProvenance, PUBLIC_MAP_MODES } from "@/data/publicSurface";
import { LAB, NOT_CURRENT, NOT_LIVE, PRODUCT, PRODUCT_EXPANSION, SURFACE } from "@/ia/copy";
import { questionById } from "@/ia/questions";
import { useDecisionStore } from "@/state/store";
import { ActionPanel } from "@/components/action/ActionPanel";
import { EvidenceLedger } from "@/components/ledger/EvidenceLedger";
import { MethodPanel } from "@/components/method/MethodPanel";
import { QuestionNav } from "@/components/navigation/QuestionNav";
import { QuestionView } from "@/views/QuestionView";

export function ProductShell() {
  const questionId = useDecisionStore((state) => state.questionId);
  const mapModeId = useDecisionStore((state) => state.mapModeId);
  const selectedAreaId = useDecisionStore((state) => state.selectedAreaId);
  const compareAreaId = useDecisionStore((state) => state.compareAreaId);
  const methodOpen = useDecisionStore((state) => state.methodOpen);
  const selectQuestion = useDecisionStore((state) => state.selectQuestion);
  const selectMapMode = useDecisionStore((state) => state.selectMapMode);
  const selectArea = useDecisionStore((state) => state.selectArea);
  const setCompareArea = useDecisionStore((state) => state.setCompareArea);
  const toggleMethod = useDecisionStore((state) => state.toggleMethod);

  const question = questionById(questionId);
  const mapMode =
    PUBLIC_MAP_MODES.find((mode) => mode.id === mapModeId) ?? PUBLIC_MAP_MODES[0];
  if (!mapMode) {
    throw new Error("Map modes missing");
  }

  return (
    <div className="shell" data-testid="decision-shell">
      <a className="skip-link" href="#decision-main">
        Skip to question
      </a>
      <header className="banner">
        <div>
          <p className="banner-kicker">{LAB}</p>
          <h1>
            {PRODUCT} {SURFACE}
          </h1>
          <p className="banner-expansion">{PRODUCT_EXPANSION}</p>
        </div>
        <div className="banner-meta">
          <p className="chip">{NOT_LIVE}</p>
          <p className="chip">{NOT_CURRENT}</p>
          <p className="lab-chip chip">{LAB}</p>
        </div>
      </header>
      <EvidenceLedger />
      <div className="body">
        <QuestionNav activeId={questionId} onSelect={selectQuestion} />
        <main>
          <QuestionView
            question={question}
            areas={ANALYSIS_AREAS}
            mapMode={mapMode}
            selectedAreaId={selectedAreaId}
            compareAreaId={compareAreaId}
            onSelectArea={selectArea}
            onSelectMode={selectMapMode}
            onCompare={setCompareArea}
          />
        </main>
        <ActionPanel questionId={questionId} />
      </div>
      <MethodPanel
        provenance={publicProvenance()}
        openId={methodOpen}
        onToggle={toggleMethod}
      />
    </div>
  );
}
