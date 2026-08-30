/** Prompt-15 product questions. Navigation only. Not backend metric names. */

export type ProductQuestionId =
  | "thermal-conditions"
  | "own-history"
  | "matched-nighttime"
  | "observed-times"
  | "area-different"
  | "nearby-support"
  | "verify-before-action";

export type ProductQuestion = {
  id: ProductQuestionId;
  index: number;
  prompt: string;
  short: string;
  target: string;
};

export const PRODUCT_QUESTIONS: readonly ProductQuestion[] = [
  {
    id: "thermal-conditions",
    index: 1,
    prompt: "What are thermal conditions here?",
    short: "Thermal conditions",
    target: "thermal-conditions",
  },
  {
    id: "own-history",
    index: 2,
    prompt: "How does this compare with the area's own history?",
    short: "Own history",
    target: "own-history",
  },
  {
    id: "matched-nighttime",
    index: 3,
    prompt: "How have matched nighttime conditions changed across years?",
    short: "Across years",
    target: "matched-nighttime",
  },
  {
    id: "observed-times",
    index: 4,
    prompt: "How did conditions differ across the observed times?",
    short: "Observed times",
    target: "observed-times",
  },
  {
    id: "area-different",
    index: 5,
    prompt: "What makes this area different?",
    short: "What is different",
    target: "area-different",
  },
  {
    id: "nearby-support",
    index: 6,
    prompt: "What support is identified nearby?",
    short: "Nearby support",
    target: "nearby-support",
  },
  {
    id: "verify-before-action",
    index: 7,
    prompt: "What should be verified before action?",
    short: "Verify first",
    target: "verify-before-action",
  },
];
