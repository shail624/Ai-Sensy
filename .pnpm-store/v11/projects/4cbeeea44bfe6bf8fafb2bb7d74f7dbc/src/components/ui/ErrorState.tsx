interface ErrorStateProps {
  message: string;
  onRetry?: () => void;
}

/** Inline error surface with an optional retry action. */
export function ErrorState({ message, onRetry }: ErrorStateProps): JSX.Element {
  return (
    <div role="alert" className="rounded-md border border-danger px-3 py-2 text-sm text-danger">
      <p>{message}</p>
      {onRetry ? (
        <button
          type="button"
          onClick={onRetry}
          className="mt-2 rounded border border-danger px-2 py-1 text-xs hover:bg-hover"
        >
          Retry
        </button>
      ) : null}
    </div>
  );
}
