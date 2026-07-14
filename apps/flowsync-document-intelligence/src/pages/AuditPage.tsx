import { ScrollText, ShieldCheck } from "lucide-react";
import { useEffect, useState } from "react";
import { createApiClient } from "../api/client";
import { listAuditEvents } from "../api/audit";
import { toSafeClientError } from "../api/errors";
import { DataTable, type DataTableColumn } from "../components/DataTable";
import { EmptyState } from "../components/EmptyState";
import { LoadingState } from "../components/LoadingState";
import { ReadOnlyNotice } from "../components/ReadOnlyNotice";
import { SafeErrorState } from "../components/SafeErrorState";
import { StatusCard } from "../components/StatusCard";
import { auditSummary } from "../state/operationalViewModels";
import { displayLabel, formatDateTime } from "../state/documentViewModels";
import type { RequestState } from "../state/requestState";
import type { AuditEventSummary } from "../types/audit";

const COLUMNS: readonly DataTableColumn<AuditEventSummary>[] = [
  { key: "event", header: "Event", render: (row) => <div className="document-cell"><strong>{displayLabel(row.event_type)}</strong><span>{row.event_id}</span></div> },
  { key: "actor", header: "Actor", render: (row) => row.actor_id },
  { key: "document", header: "Document", render: (row) => row.document_id ?? "Not available" },
  { key: "review", header: "Review case", render: (row) => row.review_case_id ?? "Not available" },
  { key: "timestamp", header: "Timestamp", render: (row) => formatDateTime(row.occurred_at) },
  { key: "summary", header: "Safe summary", render: (row) => auditSummary(row) },
];

export function AuditPage() {
  const [reloadKey, setReloadKey] = useState(0);
  const [state, setState] = useState<RequestState<AuditEventSummary[]>>({ status: "loading" });
  useEffect(() => {
    let active = true;
    setState({ status: "loading" });
    listAuditEvents(createApiClient()).then((result) => {
      const data = result.data ?? [];
      if (active) setState(data.length ? { status: "success", data } : { status: "empty" });
    }).catch((error) => { if (active) setState({ status: "error", error: toSafeClientError(error) }); });
    return () => { active = false; };
  }, [reloadKey]);
  if (state.status === "loading") return <LoadingState label="Loading audit history" />;
  if (state.status === "error") return <SafeErrorState error={state.error} onRetry={() => setReloadKey((v) => v + 1)} />;
  if (state.status !== "success") return <EmptyState title="No audit events" message="The API returned no safe audit events for this view." />;
  const eventTypes = new Set(state.data.map((item) => item.event_type)).size;
  const systemEvents = state.data.filter((item) => item.actor_id === "system").length;
  return <div className="page-stack">
    <section className="page-heading"><div><span className="eyebrow">Governance</span><h2>Audit logs</h2><p>Allowlisted event summaries from the Document Intelligence API.</p></div><ReadOnlyNotice message="Only privacy-safe audit projections are displayed." /></section>
    <section className="status-grid status-grid--three"><StatusCard label="Audit events" value={String(state.data.length)} detail="Current API result" icon={<ScrollText size={18} />} /><StatusCard label="Event types" value={String(eventTypes)} detail="Distinct safe event categories" /><StatusCard label="System events" value={String(systemEvents)} detail="Recorded system activity" tone="positive" icon={<ShieldCheck size={18} />} /></section>
    <section className="content-section"><div className="section-heading"><div><span className="eyebrow">Event register</span><h2>Audit activity</h2></div></div><DataTable caption="Audit events" columns={COLUMNS} rows={state.data} rowKey={(row) => row.event_id} /></section>
  </div>;
}
