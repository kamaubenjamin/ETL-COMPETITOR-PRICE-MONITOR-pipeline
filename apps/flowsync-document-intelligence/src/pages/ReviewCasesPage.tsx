import { AlertCircle, ClipboardCheck, UserRoundCheck } from "lucide-react";
import { useEffect, useState } from "react";
import { Link } from "react-router-dom";
import { createApiClient } from "../api/client";
import { toSafeClientError } from "../api/errors";
import { listReviewCases } from "../api/reviews";
import { DataTable, type DataTableColumn } from "../components/DataTable";
import { EmptyState } from "../components/EmptyState";
import { LoadingState } from "../components/LoadingState";
import { PriorityBadge } from "../components/PriorityBadge";
import { ReadOnlyNotice } from "../components/ReadOnlyNotice";
import { SafeErrorState } from "../components/SafeErrorState";
import { StatusCard } from "../components/StatusCard";
import { StatusChip } from "../components/StatusChip";
import { formatDateTime } from "../state/documentViewModels";
import { reviewMetrics } from "../state/operationalViewModels";
import type { RequestState } from "../state/requestState";
import type { ReviewCaseSummary } from "../types/review";

const COLUMNS: readonly DataTableColumn<ReviewCaseSummary>[] = [
  { key: "case", header: "Review case", render: (row) => <div className="document-cell"><Link to={`/review/${encodeURIComponent(row.review_case_id)}`}>{row.review_case_id}</Link><span>{row.reason_code}</span></div> },
  { key: "document", header: "Document", render: (row) => <Link className="back-link" to={`/documents/${encodeURIComponent(row.document_id)}`}>{row.document_id}</Link> },
  { key: "status", header: "Status", render: (row) => <StatusChip status={row.status} /> },
  { key: "priority", header: "Priority", render: (row) => <PriorityBadge priority={row.priority} /> },
  { key: "reviewer", header: "Assigned reviewer", render: (row) => row.assigned_reviewer ?? "Unassigned" },
  { key: "created", header: "Created", render: (row) => formatDateTime(row.created_at) },
  { key: "updated", header: "Updated", render: (row) => formatDateTime(row.updated_at) },
];

export function ReviewCasesPage() {
  const [reloadKey, setReloadKey] = useState(0);
  const [state, setState] = useState<RequestState<ReviewCaseSummary[]>>({ status: "loading" });
  useEffect(() => {
    let active = true;
    setState({ status: "loading" });
    listReviewCases(createApiClient()).then((result) => {
      const data = result.data ?? [];
      if (active) setState(data.length ? { status: "success", data } : { status: "empty" });
    }).catch((error) => { if (active) setState({ status: "error", error: toSafeClientError(error) }); });
    return () => { active = false; };
  }, [reloadKey]);
  if (state.status === "loading") return <LoadingState label="Loading review queue" />;
  if (state.status === "error") return <SafeErrorState error={state.error} onRetry={() => setReloadKey((v) => v + 1)} />;
  if (state.status !== "success") return <EmptyState title="No review cases" message="The API returned no review cases for the current view." />;
  const metrics = reviewMetrics(state.data);
  return <div className="page-stack">
    <section className="page-heading"><div><span className="eyebrow">Human review</span><h2>Review queue</h2><p>Read-only workload and case context from the Document Intelligence API.</p></div><ReadOnlyNotice message="Decisions and corrections are not available in this view." /></section>
    <section className="status-grid status-grid--five">
      <StatusCard label="Total cases" value={String(metrics.total)} detail="Current API result" icon={<ClipboardCheck size={18} />} />
      <StatusCard label="Review required" value={String(metrics.required)} detail="Awaiting triage" tone={metrics.required ? "critical" : "positive"} icon={<AlertCircle size={18} />} />
      <StatusCard label="In review" value={String(metrics.inReview)} detail="Assigned workload" tone={metrics.inReview ? "warning" : "neutral"} />
      <StatusCard label="Closed" value={String(metrics.closed)} detail="Approved, rejected, skipped or resolved" tone="positive" icon={<UserRoundCheck size={18} />} />
      <StatusCard label="High priority" value={String(metrics.highPriority)} detail="High or urgent" tone={metrics.highPriority ? "critical" : "neutral"} />
    </section>
    <section className="content-section"><div className="section-heading"><div><span className="eyebrow">Cases</span><h2>Current review workload</h2></div></div><DataTable caption="Review cases" columns={COLUMNS} rows={state.data} rowKey={(row) => row.review_case_id} /></section>
  </div>;
}
