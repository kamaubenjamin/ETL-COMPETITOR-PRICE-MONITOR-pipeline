import { Search } from "lucide-react";
import { useEffect, useMemo, useState } from "react";
import { Link } from "react-router-dom";
import { createApiClient } from "../api/client";
import { listDocuments } from "../api/documents";
import { toSafeClientError } from "../api/errors";
import { DataTable, type DataTableColumn } from "../components/DataTable";
import { DocumentSummaryCards } from "../components/DocumentSummaryCards";
import { EmptyState } from "../components/EmptyState";
import { LoadingState } from "../components/LoadingState";
import { SafeErrorState } from "../components/SafeErrorState";
import { StatusChip } from "../components/StatusChip";
import { toDocumentRow, toDocumentSummaryMetrics } from "../state/documentViewModels";
import type { RequestState } from "../state/requestState";
import type { DocumentStatus, DocumentSummary, DocumentType } from "../types/document";
import type { DocumentRowViewModel, DocumentSummaryMetric } from "../types/viewModels";

interface DocumentsPageData {
  documents: DocumentSummary[];
  rows: DocumentRowViewModel[];
  metrics: DocumentSummaryMetric[];
  total: number;
}

const STATUS_OPTIONS: Array<{ value: "" | DocumentStatus; label: string }> = [
  { value: "", label: "All statuses" },
  { value: "received", label: "Received" },
  { value: "ingested", label: "Ingested" },
  { value: "classified", label: "Classified" },
  { value: "parsed", label: "Parsed" },
  { value: "extracted", label: "Extracted" },
  { value: "transformed", label: "Transformed" },
  { value: "validated", label: "Validated" },
  { value: "matched", label: "Matched" },
  { value: "review_required", label: "Review required" },
  { value: "approved", label: "Approved" },
  { value: "export_ready", label: "Export ready" },
  { value: "exported", label: "Exported" },
  { value: "failed", label: "Failed" },
];

const TYPE_OPTIONS: Array<{ value: "" | DocumentType; label: string }> = [
  { value: "", label: "All document types" },
  { value: "invoice", label: "Invoice" },
  { value: "purchase_order", label: "Purchase order" },
  { value: "receipt", label: "Receipt" },
];

const COLUMNS: readonly DataTableColumn<DocumentRowViewModel>[] = [
  {
    key: "document",
    header: "Document",
    render: (row) => (
      <div className="document-cell">
        <Link to={`/documents/${encodeURIComponent(row.id)}`}>{row.id}</Link>
        <span>{row.filename}</span>
      </div>
    ),
  },
  { key: "type", header: "Type", render: (row) => row.type },
  { key: "status", header: "Status", render: (row) => <StatusChip status={row.status} label={row.statusLabel} /> },
  { key: "stage", header: "Current stage", render: (row) => row.currentStage },
  { key: "confidence", header: "Confidence", render: (row) => row.confidence },
  { key: "received", header: "Received", render: (row) => row.receivedAt },
  { key: "updated", header: "Updated", render: (row) => row.updatedAt },
  { key: "source", header: "Source", render: (row) => row.source },
];

export function DocumentsPage() {
  const [statusFilter, setStatusFilter] = useState<"" | DocumentStatus>("");
  const [typeFilter, setTypeFilter] = useState<"" | DocumentType>("");
  const [search, setSearch] = useState("");
  const [reloadKey, setReloadKey] = useState(0);
  const [state, setState] = useState<RequestState<DocumentsPageData>>({ status: "loading" });

  useEffect(() => {
    let active = true;
    setState({ status: "loading" });

    const load = async () => {
      try {
        const envelope = await listDocuments(createApiClient(), {
          ...(statusFilter ? { status: statusFilter } : {}),
          ...(typeFilter ? { document_type: typeFilter } : {}),
          limit: 100,
          offset: 0,
        });
        if (!active) return;
        const documents = envelope.data;
        if (!documents) {
          setState({ status: "error", error: toSafeClientError(null) });
          return;
        }
        if (documents.length === 0) {
          setState({ status: "empty" });
          return;
        }
        setState({
          status: "success",
          data: {
            documents,
            rows: documents.map(toDocumentRow),
            metrics: toDocumentSummaryMetrics(documents),
            total: envelope.metadata.pagination?.total ?? documents.length,
          },
        });
      } catch (error) {
        if (active) setState({ status: "error", error: toSafeClientError(error) });
      }
    };
    void load();
    return () => { active = false; };
  }, [statusFilter, typeFilter, reloadKey]);

  const visibleRows = useMemo(() => {
    if (state.status !== "success") return [];
    const normalized = search.trim().toLocaleLowerCase();
    return normalized ? state.data.rows.filter((row) => row.searchText.includes(normalized)) : state.data.rows;
  }, [search, state]);

  return (
    <div className="page-stack">
      <section className="page-heading">
        <div>
          <span className="eyebrow">Operational overview</span>
          <h2>Document workload</h2>
          <p>Secure read-first workspace for document processing status.</p>
        </div>
        <span className="read-only-label">API-authoritative read</span>
      </section>

      {state.status === "success" ? <DocumentSummaryCards metrics={state.data.metrics} /> : null}

      <section className="content-section">
        <div className="section-heading">
          <div><span className="eyebrow">Documents</span><h2>Inbox</h2></div>
          <span className="read-only-label">Read-only</span>
        </div>

        <div className="filter-toolbar" aria-label="Document filters">
          <label className="search-field">
            <span className="visually-hidden">Search current results</span>
            <Search size={16} aria-hidden="true" />
            <input
              type="search"
              value={search}
              onChange={(event) => setSearch(event.target.value)}
              placeholder="Search current results"
              disabled={state.status !== "success"}
            />
          </label>
          <label>
            <span className="visually-hidden">Filter by document status</span>
            <select value={statusFilter} onChange={(event) => setStatusFilter(event.target.value as "" | DocumentStatus)}>
              {STATUS_OPTIONS.map((option) => <option key={option.value || "all"} value={option.value}>{option.label}</option>)}
            </select>
          </label>
          <label>
            <span className="visually-hidden">Filter by document type</span>
            <select value={typeFilter} onChange={(event) => setTypeFilter(event.target.value as "" | DocumentType)}>
              {TYPE_OPTIONS.map((option) => <option key={option.value || "all"} value={option.value}>{option.label}</option>)}
            </select>
          </label>
          <span className="filter-note">Filters narrow API reads; access remains API-controlled.</span>
        </div>

        {state.status === "loading" ? <LoadingState label="Loading documents" /> : null}
        {state.status === "empty" ? <EmptyState title="No documents found" message="No documents match the selected API filters." /> : null}
        {state.status === "error" ? <SafeErrorState error={state.error} onRetry={() => setReloadKey((value) => value + 1)} /> : null}
        {state.status === "success" && visibleRows.length === 0 ? (
          <EmptyState title="No current results match" message="Clear or change the current-result search." />
        ) : null}
        {state.status === "success" && visibleRows.length > 0 ? (
          <>
            <div className="result-summary">
              <span>Showing {visibleRows.length} of {state.data.total} API result{state.data.total === 1 ? "" : "s"}</span>
              <span>Search applies to the loaded result set.</span>
            </div>
            <DataTable caption="Document inbox" columns={COLUMNS} rows={visibleRows} rowKey={(row) => row.id} />
          </>
        ) : null}
      </section>
    </div>
  );
}
