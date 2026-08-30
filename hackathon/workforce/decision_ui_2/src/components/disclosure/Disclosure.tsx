type DisclosureProps = {
  readonly summary: string;
  readonly children: string;
  readonly testId?: string;
};

export function Disclosure({ summary, children, testId }: DisclosureProps) {
  return (
    <details className="method-detail" data-testid={testId}>
      <summary>{summary}</summary>
      <p>{children}</p>
    </details>
  );
}
