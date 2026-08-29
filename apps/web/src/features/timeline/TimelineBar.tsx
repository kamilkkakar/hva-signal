const STAGES = ["Current", "Forecast", "Scenario", "Overnight"] as const;

export function TimelineBar() {
  return (
    <footer className="timeline" aria-label="Timeline">
      <ol>
        {STAGES.map((stage, index) => (
          <li key={stage} data-active={index === 0 ? "true" : "false"}>
            <span className="timeline-index">{String(index + 1).padStart(2, "0")}</span>
            {stage}
          </li>
        ))}
      </ol>
    </footer>
  );
}
