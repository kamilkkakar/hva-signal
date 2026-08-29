import { useState, type FormEvent } from "react";
import type { DataMode } from "@/types";
import { GRANULARITIES } from "@/api/analysisJobs";
import { useJobStore } from "@/stores/jobStore";

function toDatetimeLocalValue(date: Date): string {
  const pad = (value: number) => String(value).padStart(2, "0");
  return `${date.getFullYear()}-${pad(date.getMonth() + 1)}-${pad(date.getDate())}T${pad(date.getHours())}:${pad(date.getMinutes())}`;
}

function localInputToIso(value: string): string {
  const parsed = new Date(value);
  if (Number.isNaN(parsed.getTime())) {
    throw new Error("Analysis time is invalid.");
  }
  return parsed.toISOString();
}

export function QueryRail() {
  const submit = useJobStore((state) => state.submit);
  const submitting = useJobStore((state) => state.submitting);
  const error = useJobStore((state) => state.error);

  const [areaId, setAreaId] = useState("phoenix-demo");
  const [analysisTime, setAnalysisTime] = useState(() =>
    toDatetimeLocalValue(new Date()),
  );
  const [analysisMode, setAnalysisMode] = useState<
    "operational" | "retrospective"
  >("operational");
  const [horizonHours, setHorizonHours] = useState(12);
  const [granularity, setGranularity] = useState<(typeof GRANULARITIES)[number]>(
    100,
  );
  const [dataMode, setDataMode] = useState<DataMode>("replay");
  const [formError, setFormError] = useState<string | null>(null);

  async function onSubmit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    setFormError(null);
    try {
      await submit({
        area_id: areaId,
        analysis_time: localInputToIso(analysisTime),
        analysis_mode: analysisMode,
        horizon_hours: horizonHours,
        granularity_m: granularity,
        data_mode: dataMode,
      });
    } catch (err) {
      setFormError(err instanceof Error ? err.message : "Submit failed.");
    }
  }

  return (
    <aside className="rail" aria-label="Query rail">
      <header className="rail-head">
        <p className="kicker">Query</p>
        <h2>Run analysis</h2>
      </header>

      <form className="query-form" onSubmit={(event) => void onSubmit(event)}>
        <label>
          Area
          <input
            name="area_id"
            value={areaId}
            onChange={(event) => setAreaId(event.target.value)}
            autoComplete="off"
            required
          />
        </label>
        <label>
          Analysis time
          <input
            type="datetime-local"
            name="analysis_time"
            value={analysisTime}
            onChange={(event) => setAnalysisTime(event.target.value)}
            required
          />
        </label>
        <label>
          Mode
          <select
            name="analysis_mode"
            value={analysisMode}
            onChange={(event) =>
              setAnalysisMode(
                event.target.value as "operational" | "retrospective",
              )
            }
          >
            <option value="operational">Operational (0–12h)</option>
            <option value="retrospective">Retrospective</option>
          </select>
        </label>
        <label>
          Horizon (hours)
          <input
            type="number"
            name="horizon_hours"
            min={0}
            max={12}
            step={1}
            value={horizonHours}
            onChange={(event) => setHorizonHours(Number(event.target.value))}
            required
          />
        </label>
        <label>
          Granularity
          <select
            name="granularity_m"
            value={granularity}
            onChange={(event) =>
              setGranularity(
                Number(event.target.value) as (typeof GRANULARITIES)[number],
              )
            }
          >
            {GRANULARITIES.map((meters) => (
              <option key={meters} value={meters}>
                {meters} m
              </option>
            ))}
          </select>
        </label>
        <label>
          Data mode
          <select
            name="data_mode"
            value={dataMode}
            onChange={(event) => setDataMode(event.target.value as DataMode)}
          >
            <option value="replay">Replay</option>
            <option value="auto">Auto</option>
            <option value="live">Live</option>
          </select>
        </label>
        <button type="submit" className="submit-btn" disabled={submitting}>
          {submitting ? "Submitting" : "Submit analysis"}
        </button>
        {(formError || error) && (
          <p className="form-error" role="alert">
            {formError ?? error}
          </p>
        )}
      </form>

      <div className="copilot-lock">
        <p className="kicker">Copilot</p>
        <textarea
          disabled
          rows={3}
          placeholder="Ask why a zone ranks, or hold a scenario."
          aria-label="Copilot query"
        />
        <p className="copilot-note">
          Copilot is locked until the deterministic core works end to end.
        </p>
      </div>
    </aside>
  );
}
