import { fieldNote, type AnalysisAreaId } from "@/contracts";
import { publicIntervention } from "@/data/publicSurface";
import { INTERVENTION_NO_EFFICACY, INTERVENTION_STAMP } from "@/ia/copy";
import { TemporalChart } from "@/components/charts/TemporalChart";

type InterventionPanelProps = {
  readonly selectedAreaId: AnalysisAreaId | null;
};

export function InterventionPanel({ selectedAreaId }: InterventionPanelProps) {
  const model = publicIntervention();
  return (
    <section className="panel" aria-label="Intervention verification" data-testid="intervention-panel">
      <h3>Intervention verification</h3>
      <p className="stamp">{INTERVENTION_STAMP}</p>
      <dl className="meta-row">
        <div>
          <dt>Treated</dt>
          <dd>{model.treatedLabel}</dd>
        </div>
        <div>
          <dt>Comparison</dt>
          <dd>{model.comparisonLabel}</dd>
        </div>
        <div>
          <dt>Coverage</dt>
          <dd>{fieldNote(model.coverage)}</dd>
        </div>
        <div>
          <dt>Period</dt>
          <dd>{fieldNote(model.period)}</dd>
        </div>
      </dl>
      <p className="area-once">{INTERVENTION_NO_EFFICACY}</p>
      <TemporalChart model={model.chart} selectedAreaId={selectedAreaId} />
    </section>
  );
}
