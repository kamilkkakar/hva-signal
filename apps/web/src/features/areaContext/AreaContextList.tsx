import { LIST_ARIA, MAP_MODE_LABEL, ZERO_LAYER_NOTE } from "./copy";
import type { MapMode } from "./types";
import type { AreaContextListRow } from "./present";

export type AreaContextListProps = {
  rows: AreaContextListRow[];
  mode: MapMode;
  onSelectTract?: (tractId: string) => void;
};

export function AreaContextList({ rows, mode, onSelectTract }: AreaContextListProps) {
  return (
    <section
      className="area-context-list"
      aria-label={LIST_ARIA}
      data-testid="area-context-list"
    >
      <p>{ZERO_LAYER_NOTE}</p>
      <table>
        <caption>{MAP_MODE_LABEL[mode]} values for each analysis area</caption>
        <thead>
          <tr>
            <th>Census tract</th>
            <th>Tree canopy</th>
            <th>Income</th>
            <th>Older housing</th>
            <th>Inventory status</th>
          </tr>
        </thead>
        <tbody>
          {rows.map((row) => (
            <tr key={row.tractId}>
              <td>
                {onSelectTract ? (
                  <button type="button" onClick={() => onSelectTract(row.tractId)}>
                    {row.tractId}
                  </button>
                ) : (
                  row.tractId
                )}
              </td>
              <td>{row.canopy == null ? "—" : `${Math.round(row.canopy * 100)}%`}</td>
              <td>
                {row.income == null
                  ? "—"
                  : `$${Math.round(row.income).toLocaleString("en-US")}`}
              </td>
              <td>
                {row.olderHousing == null
                  ? "—"
                  : `${Math.round(row.olderHousing * 100)}%`}
              </td>
              <td>{row.coolingStatus}</td>
            </tr>
          ))}
        </tbody>
      </table>
    </section>
  );
}
