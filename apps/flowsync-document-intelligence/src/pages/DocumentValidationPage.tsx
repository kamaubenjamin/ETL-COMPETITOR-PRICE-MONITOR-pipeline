import { AlertTriangle, ArrowLeft, CheckCircle2, ListChecks } from "lucide-react";
import { useEffect, useState } from "react";
import { Link, useParams } from "react-router-dom";
import { createApiClient } from "../api/client";
import { getDocument, getDocumentValidation } from "../api/documents";
import { toSafeClientError } from "../api/errors";
import { DataTable, type DataTableColumn } from "../components/DataTable";
import { EmptyState } from "../components/EmptyState";
import { LoadingState } from "../components/LoadingState";
import { ReadOnlyNotice } from "../components/ReadOnlyNotice";
import { SafeErrorState } from "../components/SafeErrorState";
import { SeverityBadge } from "../components/SeverityBadge";
import { StatusCard } from "../components/StatusCard";
import { formatDateTime } from "../state/documentViewModels";
import { validationMetrics } from "../state/operationalViewModels";
import type { RequestState } from "../state/requestState";
import type { DocumentSummary, ValidationIssue } from "../types/document";

interface ValidationData { document: DocumentSummary; issues: ValidationIssue[]; }
const COLUMNS: readonly DataTableColumn<ValidationIssue>[] = [
  { key: "field", header: "Field", render: (row) => row.field },
  { key: "severity", header: "Severity", render: (row) => <SeverityBadge severity={row.severity} /> },
  { key: "rule", header: "Rule", render: (row) => row.rule_id },
  { key: "code", header: "Code", render: (row) => row.code },
  { key: "message", header: "Safe message", render: (row) => row.message },
];

export function DocumentValidationPage() {
  const { documentId } = useParams<{ documentId: string }>();
  const [reloadKey, setReloadKey] = useState(0);
  const [state, setState] = useState<RequestState<ValidationData>>({ status: "loading" });
  useEffect(() => {
    let active = true;
    setState({ status: "loading" });
    if (!documentId) {
      setState({ status: "error", error: toSafeClientError(null) });
      return () => { active = false; };
    }
    const client = createApiClient();
    Promise.all([getDocument(client, documentId), getDocumentValidation(client, documentId)])
      .then(([document, issues]) => {
        if (!active) return;
        if (!document.data || !issues.data) setState({ status: "error", error: toSafeClientError(null) });
        else setState({ status: "success", data: { document: document.data, issues: issues.data } });
      })
      .catch((error) => { if (active) setState({ status: "error", error: toSafeClientError(error) }); });
    return () => { active = false; };
  }, [documentId, reloadKey]);
  if (state.status === "loading") return <LoadingState label="Loading validation summary" />;
  if (state.status === "error") return <SafeErrorState error={state.error} onRetry={() => setReloadKey((v) => v + 1)} />;
  if (state.status !== "success") return <EmptyState title="Validation unavailable" message="No safe validation summary was returned." />;
  const metrics = validationMetrics(state.data.issues);
  return <div className="page-stack">
    <section className="page-heading"><div><Link className="back-link" to={`/documents/${encodeURIComponent(state.data.document.document_id)}`}><ArrowLeft size={16} /> Document</Link><span className="eyebrow">Validation</span><h2>{state.data.document.filename}</h2><p>{state.data.document.document_id} - Updated {formatDateTime(state.data.document.updated_at)}</p></div><ReadOnlyNotice /></section>
    <section className="status-grid">
      <StatusCard label="Validation status" value={metrics.status} detail="Safe issue projection" tone={metrics.errors ? "critical" : metrics.warnings ? "warning" : "positive"} icon={<CheckCircle2 size={18} />} />
      <StatusCard label="Total issues" value={String(metrics.total)} detail="Current API result" icon={<ListChecks size={18} />} />
      <StatusCard label="Errors" value={String(metrics.errors)} detail="Requires attention" tone={metrics.errors ? "critical" : "positive"} icon={<AlertTriangle size={18} />} />
      <StatusCard label="Warnings" value={String(metrics.warnings)} detail="Operator confirmation" tone={metrics.warnings ? "warning" : "positive"} />
    </section>
    <section className="content-section"><div className="section-heading"><div><span className="eyebrow">Issue register</span><h2>Validation issues</h2></div></div>{state.data.issues.length ? <DataTable caption="Validation issues" columns={COLUMNS} rows={state.data.issues} rowKey={(row) => row.issue_id} /> : <EmptyState title="No validation issues" message="The API returned no safe issue records for this document." />}</section>
  </div>;
}
