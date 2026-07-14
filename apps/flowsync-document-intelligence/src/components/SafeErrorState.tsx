import { AlertTriangle, LockKeyhole, WifiOff } from "lucide-react";
import type { SafeClientError } from "../api/errors";

interface SafeErrorStateProps {
  error: SafeClientError;
}

export function SafeErrorState({ error }: SafeErrorStateProps) {
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
    </section>
  );
}

