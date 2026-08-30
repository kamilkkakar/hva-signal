import { LIST_ARIA, ZERO_LAYER_NOTE } from "./copy";
import { listCaption } from "./present";
import type { MapMode } from "./types";
import type { AreaContextListRow } from "./present";

export type AreaContextListProps = {
  rows: AreaContextListRow[];
  mode: MapMode;
  selectedZoneId?: string | null;
  onSelectTract?: (tractId: string) => void;
};

export function AreaContextList({
  rows,
  mode,
  selectedZoneId = null,
  onSelectTract,
}: AreaContextListProps) {
  return (
    <section
      className="area-context-list"
      aria-label={LIST_ARIA}
      data-testid="area-context-list"
    >
      <p>{ZERO_LAYER_NOTE}</p>
      <table>
        <caption data-testid="area-context-list-caption">{listCaption(mode)}</caption>
        <thead>
          <tr>
            <th>Analysis area</th>
            <th>Census tract</th>
            <th>Tree canopy</th>
            <th>Income</th>
            <th>Older housing</th>
            <th>Inventory status</th>
          </tr>
        </thead>
        <tbody>
          {rows.map((row) => {
            const selected = selectedZoneId === row.tractId;
            return (
              <tr key={row.tractId} data-selected={selected ? "true" : "false"}>
                <td>
                  {onSelectTract ? (
                    <button
                      type="button"
                      aria-pressed={selected}
                      onClick={() => onSelectTract(row.tractId)}
                    >
                      {row.areaLabel}
                    </button>
                  ) : (
                    row.areaLabel
                  )}
                </td>
                <td>{row.tractId}</td>
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
            );
          })}
        </tbody>
      </table>
    </section>
  );
}
