import type { ReactNode } from "react";
import type { SectionStatus } from "./types";

type StoryCardProps = {
  title: string;
  status: SectionStatus;
  children: ReactNode;
  testId: string;
};

export function StoryCard({ title, status, children, testId }: StoryCardProps) {
  return (
    <article className="decision-card" data-testid={testId} data-status={status}>
      <header>
        <h3>{title}</h3>
        <p className="decision-status">{status}</p>
      </header>
      {children}
    </article>
  );
}
