type EmptyPlotProps = {
  readonly label: string;
};

export function EmptyPlot({ label }: EmptyPlotProps) {
  return (
    <div className="plot" role="img" aria-label={label} data-testid="empty-plot" />
  );
}
