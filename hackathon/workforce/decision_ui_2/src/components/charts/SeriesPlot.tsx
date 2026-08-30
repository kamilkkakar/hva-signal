import type { SeriesPoint } from "@/contracts";

type SeriesPlotProps = {
  readonly points: readonly SeriesPoint[];
  readonly label: string;
};

export function SeriesPlot({ points, label }: SeriesPlotProps) {
  const width = 320;
  const height = 168;
  const pad = 18;
  const ys = points.map((point) => point.y);
  const min = Math.min(...ys);
  const max = Math.max(...ys);
  const span = max - min || 1;
  const coords = points.map((point, index) => {
    const x =
      pad + (index / Math.max(points.length - 1, 1)) * (width - pad * 2);
    const y = height - pad - ((point.y - min) / span) * (height - pad * 2);
    return `${x},${y}`;
  });

  return (
    <div className="plot" role="img" aria-label={label}>
      <svg viewBox={`0 0 ${width} ${height}`} aria-hidden="true">
        <polyline
          fill="none"
          stroke="#d56a1c"
          strokeWidth="2.2"
          points={coords.join(" ")}
        />
      </svg>
    </div>
  );
}
