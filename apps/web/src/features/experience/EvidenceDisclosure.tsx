import type { ReactNode } from "react";
import { ABOUT_SUMMARY, METHOD_SUMMARY } from "./copy";

type EvidenceDisclosureProps = {
  children: ReactNode;
};

export function EvidenceDisclosure({ children }: EvidenceDisclosureProps) {
  return (
    <details className="hx-disclosure" data-testid="evidence-disclosure">
      <summary>{ABOUT_SUMMARY}</summary>
      <p className="hx-note">{METHOD_SUMMARY}</p>
      {children}
    </details>
  );
}
