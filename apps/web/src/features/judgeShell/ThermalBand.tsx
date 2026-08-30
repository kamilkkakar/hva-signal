import {
  SIGNAL_A_FACT_IDLE,
  SIGNAL_A_FACT_NOT_PREPARED,
  SIGNAL_A_FACT_SHOWN,
  SIGNAL_A_FACT_WITHHELD,
  SIGNAL_A_QUESTION,
  SIGNAL_B_FACT,
  SIGNAL_B_QUESTION,
  SIGNAL_B_STAMP,
} from "./copy";
import type { HappeningStamp } from "./happening";

type ThermalBandProps = {
  stamp: HappeningStamp;
};

function signalAFact(stamp: HappeningStamp): string {
  if (stamp === "ORDER SHOWN") {
    return SIGNAL_A_FACT_SHOWN;
  }
  if (stamp === "ORDER WITHHELD") {
    return SIGNAL_A_FACT_WITHHELD;
  }
  if (stamp === "HISTORY NOT PREPARED") {
    return SIGNAL_A_FACT_NOT_PREPARED;
  }
  return SIGNAL_A_FACT_IDLE;
}

function signalAStamp(stamp: HappeningStamp): string {
  if (
    stamp === "ORDER SHOWN" ||
    stamp === "ORDER WITHHELD" ||
    stamp === "HISTORY NOT PREPARED"
  ) {
    return stamp;
  }
  return "NOT REQUESTED";
}

export function ThermalBand({ stamp }: ThermalBandProps) {
  return (
    <section className="judge-thermal" aria-label="Thermal evidence">
      <article className="judge-card" data-testid="thermal-card-a">
        <p className="kicker">Signal A</p>
        <h2>Nighttime historical</h2>
        <p className="judge-card-question">{SIGNAL_A_QUESTION}</p>
        <p className="judge-stamp judge-stamp-sm" data-testid="signal-a-stamp">
          {signalAStamp(stamp)}
        </p>
        <p className="judge-card-fact">{signalAFact(stamp)}</p>
      </article>
      <article className="judge-card" data-testid="thermal-card-b">
        <p className="kicker">Signal B</p>
        <h2>Selected-time snapshot</h2>
        <p className="judge-card-question">{SIGNAL_B_QUESTION}</p>
        <p className="judge-stamp judge-stamp-sm" data-testid="signal-b-stamp">
          {SIGNAL_B_STAMP}
        </p>
        <p className="judge-card-fact">{SIGNAL_B_FACT}</p>
      </article>
    </section>
  );
}
