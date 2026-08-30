import type { ProvenanceModel } from "@/contracts";

type MethodPanelProps = {
  readonly provenance: ProvenanceModel;
  readonly openId: "why" | "method" | "evidence" | null;
  readonly onToggle: (id: "why" | "method" | "evidence") => void;
};

const TOGGLES = [
  { id: "why" as const, itemId: "why" },
  { id: "method" as const, itemId: "method" },
  { id: "evidence" as const, itemId: "evidence" },
];

export function MethodPanel({ provenance, openId, onToggle }: MethodPanelProps) {
  const openItem = provenance.items.find((item) => item.id === openId) ?? null;
  return (
    <footer className="method-bar" data-testid="method-panel">
      <h2>Method and provenance</h2>
      <dl className="meta-row">
        <div>
          <dt>Source</dt>
          <dd>{provenance.source}</dd>
        </div>
        <div>
          <dt>Clock</dt>
          <dd>{provenance.clock}</dd>
        </div>
        <div>
          <dt>Geography</dt>
          <dd>{provenance.geography}</dd>
        </div>
      </dl>
      <div className="method-actions">
        {TOGGLES.map((toggle) => {
          const item = provenance.items.find((entry) => entry.id === toggle.itemId);
          if (!item) {
            return null;
          }
          return (
            <button
              key={toggle.id}
              type="button"
              aria-expanded={openId === toggle.id}
              onClick={() => onToggle(toggle.id)}
            >
              {item.label}
            </button>
          );
        })}
      </div>
      {openItem ? <p className="method-detail">{openItem.detail}</p> : null}
      {provenance.items
        .filter((item) => item.id !== "why" && item.id !== "method" && item.id !== "evidence")
        .map((item) => (
          <details key={item.id} className="method-detail">
            <summary>{item.label}</summary>
            <p>{item.detail}</p>
          </details>
        ))}
    </footer>
  );
}
