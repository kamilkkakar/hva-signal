import { create } from "zustand";
import type { AnalysisAreaId, MapModeId, QuestionId } from "@/contracts";
import { questionById } from "@/ia/questions";

export type DecisionState = {
  questionId: QuestionId;
  mapModeId: MapModeId;
  selectedAreaId: AnalysisAreaId | null;
  compareAreaId: AnalysisAreaId | null;
  methodOpen: "why" | "method" | "evidence" | null;
  selectQuestion: (id: QuestionId) => void;
  selectMapMode: (id: MapModeId) => void;
  selectArea: (id: AnalysisAreaId) => void;
  setCompareArea: (id: AnalysisAreaId | null) => void;
  toggleMethod: (id: "why" | "method" | "evidence") => void;
};

export const INITIAL_DECISION_STATE = {
  questionId: "at-this-time" as QuestionId,
  mapModeId: "selected_time" as MapModeId,
  selectedAreaId: null,
  compareAreaId: null,
  methodOpen: null,
};

export function resetDecisionStore() {
  useDecisionStore.setState({
    ...INITIAL_DECISION_STATE,
  });
}

export const useDecisionStore = create<DecisionState>((set, get) => ({
  ...INITIAL_DECISION_STATE,
  selectQuestion: (id) => {
    const question = questionById(id);
    set({ questionId: id, mapModeId: question.mapMode });
  },
  selectMapMode: (id) => set({ mapModeId: id }),
  selectArea: (id) => {
    const { selectedAreaId } = get();
    set({ selectedAreaId: selectedAreaId === id ? null : id });
  },
  setCompareArea: (id) => set({ compareAreaId: id }),
  toggleMethod: (id) => {
    set({ methodOpen: get().methodOpen === id ? null : id });
  },
}));
