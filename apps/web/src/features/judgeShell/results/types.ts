export type ResultStamp =
  | "NOT REQUESTED"
  | "WORKING"
  | "ORDER SHOWN"
  | "ORDER WITHHELD"
  | "HISTORY NOT PREPARED"
  | "FAILED"
  | "NOT ON THIS SURFACE"
  | "AVAILABLE NOW — CACHED EVIDENCE";

export type ResultValue = {
  label: string;
  value: string;
};

export type ResultCardModel = {
  id: "a" | "b";
  kicker: string;
  title: string;
  question: string;
  stamp: ResultStamp | string;
  message: string;
  values: ResultValue[];
};

export type ResultCardsView = {
  a: ResultCardModel;
  b: ResultCardModel;
};
