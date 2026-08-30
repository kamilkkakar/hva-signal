import {
  CAPABILITY_NEXT,
  CAPABILITY_NEXT_ITEMS,
  CAPABILITY_NOT,
  CAPABILITY_NOT_ITEMS,
  CAPABILITY_ON,
  CAPABILITY_ON_ITEMS,
  CAPABILITY_TITLE,
} from "./copy";

function Column({
  title,
  items,
  testId,
}: {
  title: string;
  items: readonly { noun: string; status: string }[];
  testId: string;
}) {
  return (
    <div data-testid={testId}>
      <p className="kicker">{title}</p>
      <ul>
        {items.map((item) => (
          <li key={item.noun}>
            <span>{item.noun}</span>
            <span className="judge-cap-status">{item.status}</span>
          </li>
        ))}
      </ul>
    </div>
  );
}

export function CapabilityBand() {
  return (
    <section
      className="judge-capability"
      aria-label={CAPABILITY_TITLE}
      data-testid="capability-band"
    >
      <h2>{CAPABILITY_TITLE}</h2>
      <div className="judge-capability-grid">
        <Column title={CAPABILITY_ON} items={CAPABILITY_ON_ITEMS} testId="capability-on" />
        <Column
          title={CAPABILITY_NEXT}
          items={CAPABILITY_NEXT_ITEMS}
          testId="capability-next"
        />
        <Column title={CAPABILITY_NOT} items={CAPABILITY_NOT_ITEMS} testId="capability-not" />
      </div>
    </section>
  );
}
