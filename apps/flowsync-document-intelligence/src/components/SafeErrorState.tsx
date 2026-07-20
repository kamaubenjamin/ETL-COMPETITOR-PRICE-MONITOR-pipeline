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
  const detail = error.kind === "unauthorized"
    ? "Authentication is handled outside this application."
    : error.kind === "forbidden"
      ? "Access is enforced by the Document Intelligence API."
      : error.kind === "not_found"
        ? "The resource may not exist or may be outside your current access scope."
        : error.kind === "conflict"
          ? "Review the latest API version before applying your changes. Nothing was overwritten."
        : error.kind === "invalid_response"
          ? "No data was displayed because the response could not be safely validated."
          : error.kind === "auth_mismatch"
            ? "Contact the environment owner to review access configuration."
            : error.kind === "configuration"
              ? "The environment owner must configure the exact HTTPS API origin before this hosted preview can load data."
            : error.kind === "runtime_unavailable"
              ? "The application remains read-only while runtime services are unavailable."
              : "No protected data was loaded.";

  return (
    <section className="safe-error-state" role="status">
      <Icon size={24} aria-hidden="true" />
      <h2>{error.message}</h2>
      <p>{detail}</p>
      {error.requestId ? <span>Support reference: {error.requestId}</span> : null}
      {onRetry ? (
        <button className="secondary-button" type="button" onClick={onRetry}>
          <RefreshCw size={16} aria-hidden="true" /> Retry read
        </button>
      ) : null}
    </section>
  );
}
