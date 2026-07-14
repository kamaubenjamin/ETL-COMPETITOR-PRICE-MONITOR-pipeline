import { AlertTriangle, LockKeyhole, RefreshCw, WifiOff } from "lucide-react";
import type { SafeClientError } from "../api/errors";

interface SafeErrorStateProps {
  error: SafeClientError;
  onRetry?: () => void;
}

export function SafeErrorState({ error, onRetry }: SafeErrorStateProps) {
  const Icon = error.kind === "unauthorized" || error.kind === "forbidden"
    ? LockKeyhole
    : error.kind === "unavailable"
      ? WifiOff
      : AlertTriangle;

  return (
    <section className="safe-error-state" role="status">
      <Icon size={24} aria-hidden="true" />
      <h2>{error.message}</h2>
      <p>No protected data was loaded.</p>
      {error.requestId ? <span>Support reference: {error.requestId}</span> : null}
      {onRetry ? (
        <button className="secondary-button" type="button" onClick={onRetry}>
          <RefreshCw size={16} aria-hidden="true" /> Retry read
        </button>
      ) : null}
    </section>
  );
}
