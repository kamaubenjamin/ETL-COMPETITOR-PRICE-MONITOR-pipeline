import { Ban, History, PackageCheck } from "lucide-react";
import { useEffect, useState } from "react";
import { createApiClient } from "../api/client";
import { listDocumentExports } from "../api/exports";
import { displayLabel, formatDateTime } from "../state/documentViewModels";
import type { ExportAttemptSummary } from "../types/export";
import { StatusChip } from "./StatusChip";

type HistoryState = { status: "loading" } | { status: "available"; attempts: ExportAttemptSummary[] } | { status: "unavailable" };

export function ExportReadinessPanel({ documentId }: { documentId: string }) {
  const [history, setHistory] = useState<HistoryState>({ status: "loading" });
  useEffect(() => {
    let active = true;
    listDocumentExports(createApiClient(), documentId)
      .then((response) => { if (active) setHistory({ status: "available", attempts: response.data ?? [] }); })
      .catch(() => { if (active) setHistory({ status: "unavailable" }); });
    return () => { active = false; };
  }, [documentId]);
  return (
    <section className="export-readiness-panel" aria-labelledby="export-readiness-heading">
      <div className="section-heading">
        <div><span className="eyebrow">API-authoritative readiness</span><h2 id="export-readiness-heading">Export boundary planned</h2></div>
        <span className="read-only-label">Read-only</span>
      </div>
      <div className="export-readiness-grid">
        <div className="export-action-card">
          <div className="export-action-icon"><PackageCheck size={20} aria-hidden="true" /></div>
          <div><strong>Export execution is disabled until API mutation activation is approved</strong><p>ERP adapters are not connected. FlowSync does not construct export payloads or determine access.</p></div>
          <button type="button" disabled aria-disabled="true"><Ban size={15} aria-hidden="true" /> Export unavailable</button>
        </div>
        <div className="export-history-card">
          <div className="export-history-heading"><History size={18} aria-hidden="true" /><strong>Export attempt history</strong></div>
          {history.status === "loading" && <p>Loading safe API summaries…</p>}
          {history.status === "unavailable" && <p>Export history is safely unavailable from the API.</p>}
          {history.status === "available" && history.attempts.length === 0 && <p>No export attempts are available for this document.</p>}
          {history.status === "available" && history.attempts.length > 0 && <ul className="export-history-list">{history.attempts.map((attempt) => (
            <li key={attempt.attempt_id}><div><strong>{displayLabel(attempt.target_type)}</strong><span>{formatDateTime(attempt.updated_at)}</span></div><StatusChip status={attempt.result_status ?? attempt.status} /></li>
          ))}</ul>}
        </div>
      </div>
    </section>
  );
}
