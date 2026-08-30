export type ActionKind =
  | "awaiting"
  | "not_evaluated"
  | "sufficient"
  | "insufficient";

export type ActionFramingView = {
  kind: ActionKind;
  stamp: string;
  says: string;
  supports: string;
  doesNotEstablish: string;
  status: "AVAILABLE NOW — DECISION FRAMING";
  scope: string;
};
