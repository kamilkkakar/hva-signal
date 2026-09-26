import type { CityConfig, ValidationJurisdiction } from "./types";

const CAPABILITY_LABELS: Readonly<Record<string, string>> = {
  local_story: "Local HVA story",
  type1_live: "Selected-time thermal",
  selected_time_thermal: "Selected-time thermal",
  timeline: "Timeline",
  place_geometry: "Place geometry",
  catalog_entry: "Catalog entry",
};

function labelFor(value: string): string {
  return CAPABILITY_LABELS[value] ?? value.replaceAll("_", " ");
}

function stateLabel(value: string): string {
  return value.toLowerCase().replaceAll("_", " ");
}

type Props = {
  city: CityConfig;
  validationJurisdictions: readonly ValidationJurisdiction[];
};

export function CapabilityEvidenceDisclosure({ city, validationJurisdictions }: Props) {
  const evidence = Object.entries(city.capabilityEvidence ?? {});
  return (
    <details className="ws-capability-disclosure" data-testid="capability-evidence-disclosure">
      <summary>Coverage and capability evidence</summary>
      <p className="ws-capability-intro">
        These states describe available evidence, not heat severity or city rank. Only server-listed
        operational cities appear in the selector.
      </p>
      <h3>{city.label}, {city.state}</h3>
      {evidence.length > 0 ? (
        <dl className="ws-capability-list" data-testid="operational-capability-evidence">
          {evidence.map(([capability, item]) => (
            <div key={capability} className="ws-capability-item">
              <dt>{labelFor(capability)} · {stateLabel(item.state)}</dt>
              <dd>{item.reason}</dd>
              <dd><strong>Affects:</strong> {labelFor(item.affectedScope)}</dd>
              <dd><strong>Next check:</strong> {item.nextCheck}</dd>
            </div>
          ))}
        </dl>
      ) : (
        <p data-testid="capability-evidence-unavailable">
          Structured server evidence is unavailable; packaged city access remains fail-closed.
        </p>
      )}
      <h3>Validation-only coverage</h3>
      <p>These profiles are evidence checks and cannot be selected or requested from this workspace.</p>
      <ul className="ws-validation-list" data-testid="validation-only-jurisdictions">
        {validationJurisdictions.map((item) => (
          <li key={item.jurisdictionId} data-selectable="false">
            <strong>{item.displayName}{item.regionCode ? `, ${item.regionCode}` : ""}</strong>
            <span>{stateLabel(item.state)} · validation only</span>
            <p>{item.reason}</p>
            <p><strong>Next check:</strong> {item.nextCheck}</p>
          </li>
        ))}
      </ul>
    </details>
  );
}
