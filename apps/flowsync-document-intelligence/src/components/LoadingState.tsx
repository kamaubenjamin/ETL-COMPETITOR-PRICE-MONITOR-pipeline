interface LoadingStateProps {
  label?: string;
}

export function LoadingState({ label = "Loading workspace" }: LoadingStateProps) {
  return (
    <section className="loading-state" aria-busy="true" aria-label={label}>
      <div className="loading-line loading-line--wide" />
      <div className="loading-line" />
      <div className="loading-line loading-line--short" />
    </section>
  );
}

