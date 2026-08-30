import type { ChartChrome } from "@/contracts";
import type { ReactNode } from "react";

type ChartFrameProps = {
  readonly chrome: ChartChrome;
  readonly children: ReactNode;
  readonly testId?: string;
};

export function ChartFrame({ chrome, children, testId }: ChartFrameProps) {
  return (
    <figure className="chart-frame" data-testid={testId ?? "chart-frame"}>
      <h3>{chrome.title}</h3>
      <div className="chart-chrome" data-testid="chart-chrome">
        <p>
          <span>Unit</span>
          {chrome.unit}
        </p>
        <p>
          <span>Period</span>
          {chrome.period}
        </p>
        <p>
          <span>Baseline</span>
          {chrome.baseline}
        </p>
        <p>
          <span>Coverage</span>
          {chrome.coverage}
        </p>
        <p>
          <span>Source</span>
          {chrome.source}
        </p>
      </div>
      {children}
    </figure>
  );
}
