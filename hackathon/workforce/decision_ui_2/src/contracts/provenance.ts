export type ProvenanceItem = {
  readonly id: string;
  readonly label: string;
  readonly detail: string;
};

export type ProvenanceModel = {
  readonly source: string;
  readonly clock: string;
  readonly geography: string;
  readonly items: readonly ProvenanceItem[];
};
