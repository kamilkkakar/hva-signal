import type { AnalysisResultStub } from "@/api/analysisJobs";
import type { JobStatus } from "@/types";
import {
  bindHistoricalPositions,
  HistoricalPositionStrip,
  presentHistoricalPosition,
} from "../charts";
import { signalAInputFromResult } from "./fromResult";
import { presentSignalA } from "./presentation";
import { SigAHistoryLock } from "./SigAHistoryLock";
import { SigAHover } from "./SigAHover";
import { SigAMapLayer } from "./SigAMapLayer";
import { SigAMethod } from "./SigAMethod";
import { SigAOrderStamp } from "./SigAOrderStamp";
import { SigAQuestion } from "./SigAQuestion";
import { SigAWithhold } from "./SigAWithhold";
import "./signalA.css";
import type { SignalAInput, SignalAView } from "./types";

export type SignalAPanelProps = {
  view?: SignalAView;
  input?: SignalAInput;
  status?: JobStatus | null;
  result?: AnalysisResultStub | null;
  requested?: boolean;
  historyPrepared?: boolean;
  zoneId?: string;
  selectedZoneId?: string | null;
  order?: number;
};

export function SignalAPanel({
  view: given,
  input,
  status,
  result,
  requested,
  historyPrepared,
  zoneId,
  selectedZoneId,
  order,
}: SignalAPanelProps) {
  const view =
    given ??
    presentSignalA(
      input ??
        signalAInputFromResult({
          status,
          result,
          requested,
          historyPrepared,
          zoneId,
          order,
        }),
    );

  return (
    <section
      className="siga"
      data-testid="judge-signal-a"
      data-siga-kind={view.kind}
      data-siga-tone={view.tone}
      data-fills={view.rankedFillCount}
      data-blocks-b="false"
      aria-label={view.title}
    >
      <div data-testid="siga-chrome">
        <SigAQuestion view={view} />
        <p className="siga-clock" data-testid="siga-clock">
          {view.clock}
        </p>
        <p className="siga-window">{view.geography}</p>
        <SigAOrderStamp view={view} />
        <p className="decision-copy" data-testid="siga-rail">
          {view.railSentence}
        </p>
        {view.kind !== "history_not_prepared" &&
          view.kind !== "history_too_thin" && (
            <p className="decision-copy" data-testid="siga-body">
              {view.body}
            </p>
          )}
        <SigAHistoryLock view={view} />
        <SigAWithhold view={view} />
        <SigAMapLayer view={view} />
        {view.hoverLine && (
          <SigAHover
            kind={view.kind}
            zoneId={zoneId ?? input?.zoneId ?? ""}
            order={order ?? input?.order ?? 0}
          />
        )}
        <HistoricalPositionStrip
          view={presentHistoricalPosition(
            bindHistoricalPositions({
              result,
              selectedZoneId: selectedZoneId ?? null,
            }),
          )}
        />
      </div>
      <SigAMethod view={view} />
    </section>
  );
}
