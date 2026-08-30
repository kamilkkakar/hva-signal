import { presentCapabilityExpansion } from "./model";
import "./capabilities.css";

export function CapabilityExpansion() {
  const view = presentCapabilityExpansion();

  return (
    <section
      className="capability-expansion"
      data-testid="capability-expansion"
      data-fake-gauges="false"
      data-public-b="false"
      data-search-geo="disabled"
      data-hosted-live="disabled"
      data-numeric-probability="blocked"
      aria-labelledby="capability-expansion-title"
    >
      <header className="capability-head">
        <p className="kicker">{view.kicker}</p>
        <h2 id="capability-expansion-title">{view.title}</h2>
        <p className="capability-lead">{view.lead}</p>
        <dl className="capability-hva">
          {view.hva.map((item) => (
            <div key={item.letter}>
              <dt>{item.letter}</dt>
              <dd>{item.line}</dd>
            </div>
          ))}
        </dl>
      </header>

      <ol className="capability-spine" aria-label="Development stages, not live product modes">
        {view.spine.map((stage) => (
          <li key={stage}>
            <span>{stage}</span>
          </li>
        ))}
      </ol>

      <div className="capability-bands">
        {view.bands.map((band) => (
          <section
            key={band.id}
            className="capability-band"
            data-testid={`capability-band-${band.id}`}
            data-band={band.id}
          >
            <h3>{band.title}</h3>
            <ul>
              {band.rows.map((row) => (
                <li
                  key={row.id}
                  data-testid={`capability-row-${row.id}`}
                  data-capability={row.id}
                  data-maturity={row.maturity}
                  data-numeric-public={row.numericPublic ? "true" : "false"}
                >
                  <p className="capability-name">{row.name}</p>
                  <p
                    className="capability-maturity"
                    data-testid={`capability-maturity-${row.id}`}
                  >
                    {row.maturity}
                  </p>
                  <p className="capability-question">{row.question}</p>
                  <p className="capability-scope">{row.scope}</p>
                </li>
              ))}
            </ul>
          </section>
        ))}
      </div>

      <p className="capability-not-this">
        <span>Not this product</span>
        {view.notThisProduct.join(" · ")}
      </p>

      <details className="capability-modules">
        <summary>What each module is for</summary>
        <p className="capability-modules-intro">{view.modulesIntro}</p>
        <dl>
          {view.modules.map((module) => (
            <div key={module.id} data-testid={`capability-module-${module.id}`}>
              <dt>{module.name}</dt>
              <dd>
                <p>{module.what}</p>
                <p>{module.rule}</p>
              </dd>
            </div>
          ))}
        </dl>
      </details>
    </section>
  );
}
