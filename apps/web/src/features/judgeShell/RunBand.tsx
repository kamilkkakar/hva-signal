import { useState, type FormEvent } from "react";
import { useJobStore } from "@/stores/jobStore";
import {
  PHOENIX_DEMO_DEFAULT_DATE,
  phoenixAoiLocalAnalysisTime,
} from "@/utils/phoenixAoiLocalTime";
import {
  INSUFFICIENT_NIGHT_DATE,
  RUN_CLOCK_LOCK,
  RUN_INSUFFICIENT,
  RUN_KICKER,
  RUN_RESUBMIT,
  RUN_SUBMIT,
  RUN_SUFFICIENT,
  SUFFICIENT_NIGHT_DATE,
} from "./copy";

const AREA_ID = "phoenix-demo";

async function submitNight(
  submit: (draft: {
    area_id: string;
    analysis_time: string;
    analysis_mode: "retrospective";
    horizon_hours: number;
    granularity_m: number;
    data_mode: "replay";
  }) => Promise<void>,
  date: string,
): Promise<void> {
  await submit({
    area_id: AREA_ID,
    analysis_time: phoenixAoiLocalAnalysisTime(`${date}T03:00`),
    analysis_mode: "retrospective",
    horizon_hours: 12,
    granularity_m: 100,
    data_mode: "replay",
  });
}

export function RunBand() {
  const submit = useJobStore((state) => state.submit);
  const resubmit = useJobStore((state) => state.resubmit);
  const submitting = useJobStore((state) => state.submitting);
  const canResubmit = useJobStore((state) => state.canResubmit);
  const error = useJobStore((state) => state.error);
  const [date, setDate] = useState(PHOENIX_DEMO_DEFAULT_DATE);
  const [formError, setFormError] = useState<string | null>(null);

  async function runDate(nextDate: string) {
    setFormError(null);
    setDate(nextDate);
    try {
      await submitNight(submit, nextDate);
    } catch (err) {
      setFormError(err instanceof Error ? err.message : "Submit failed.");
    }
  }

  async function onSubmit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    await runDate(date);
  }

  return (
    <section className="judge-run" aria-label={RUN_KICKER} data-testid="run-band">
      <p className="kicker">{RUN_KICKER}</p>
      <p className="judge-run-lock">{RUN_CLOCK_LOCK}</p>
      <div className="judge-run-clicks">
        <button
          type="button"
          className="submit-btn"
          data-testid="run-sufficient-night"
          disabled={submitting}
          onClick={() => void runDate(SUFFICIENT_NIGHT_DATE)}
        >
          {RUN_SUFFICIENT}
        </button>
        <button
          type="button"
          className="submit-btn judge-run-secondary"
          data-testid="run-insufficient-night"
          disabled={submitting}
          onClick={() => void runDate(INSUFFICIENT_NIGHT_DATE)}
        >
          {RUN_INSUFFICIENT}
        </button>
      </div>
      <form className="judge-run-form" onSubmit={(event) => void onSubmit(event)}>
        <label>
          Date
          <input
            type="date"
            name="analysis_date"
            value={date}
            onChange={(event) => setDate(event.target.value)}
            required
          />
        </label>
        <button type="submit" className="submit-btn" disabled={submitting}>
          {submitting ? "Submitting" : RUN_SUBMIT}
        </button>
        {canResubmit && (
          <button
            type="button"
            className="submit-btn judge-run-secondary"
            data-testid="run-resubmit"
            onClick={() => void resubmit()}
          >
            {RUN_RESUBMIT}
          </button>
        )}
      </form>
      {(formError || error) && (
        <p className="form-error" role="alert">
          {formError ?? error}
        </p>
      )}
    </section>
  );
}
