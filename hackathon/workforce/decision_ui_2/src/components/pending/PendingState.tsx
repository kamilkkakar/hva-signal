type PendingStateProps = {
  readonly message: string;
  readonly testId?: string;
};

export function PendingState({ message, testId }: PendingStateProps) {
  return (
    <p className="pending" data-testid={testId ?? "pending-state"} data-availability="pending">
      {message}
    </p>
  );
}
