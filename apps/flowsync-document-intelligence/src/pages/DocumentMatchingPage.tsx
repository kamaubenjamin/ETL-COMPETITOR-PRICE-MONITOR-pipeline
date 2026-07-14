import { ArrowLeft, FileSearch, ScanSearch, Users } from "lucide-react";
import { useEffect, useState } from "react";
import { Link, useParams } from "react-router-dom";
import { createApiClient } from "../api/client";
import { getDocument, getDocumentMatching } from "../api/documents";
import { toSafeClientError } from "../api/errors";
import { ConfidenceBar } from "../components/ConfidenceBar";
import { DataTable, type DataTableColumn } from "../components/DataTable";
import { EmptyState } from "../components/EmptyState";
import { LoadingState } from "../components/LoadingState";
import { ReadOnlyNotice } from "../components/ReadOnlyNotice";
import { SafeErrorState } from "../components/SafeErrorState";
import { StatusCard } from "../components/StatusCard";
import { StatusChip } from "../components/StatusChip";
import { matchingMetrics } from "../state/operationalViewModels";
import type { RequestState } from "../state/requestState";
import type { DocumentSummary, MatchingResult } from "../types/document";

interface MatchingData { document: DocumentSummary; results: MatchingResult[]; }
const COLUMNS: readonly DataTableColumn<MatchingResult>[] = [
  { key: "candidate", header: "Candidate", render: (row) => row.candidate_id },
  { key: "confidence", header: "Confidence", render: (row) => <ConfidenceBar value={row.confidence} /> },
  { key: "source", header: "Entity type", render: (row) => row.entity_type },
  { key: "status", header: "Status", render: (row) => <StatusChip status={row.status} /> },
  { key: "reference", header: "Safe reference", render: (row) => row.match_id },
];

export function DocumentMatchingPage() {
  const { documentId } = useParams<{ documentId: string }>();
  const [reloadKey, setReloadKey] = useState(0);
  const [state, setState] = useState<RequestState<MatchingData>>({ status: "loading" });
  useEffect(() => {
    let active = true;
    setState({ status: "loading" });
    if (!documentId) { setState({ status: "error", error: toSafeClientError(null) }); return () => { active = false; }; }
    const client = createApiClient();
    Promise.all([getDocument(client, documentId), getDocumentMatching(client, documentId)])
      .then(([document, results]) => {
        if (!active) return;
        if (!document.data || !results.data) setState({ status: "error", error: toSafeClientError(null) });
        else setState({ status: "success", data: { document: document.data, results: results.data } });
      }).catch((error) => { if (active) setState({ status: "error", error: toSafeClientError(error) }); });
    return () => { active = false; };
  }, [documentId, reloadKey]);
  if (state.status === "loading") return <LoadingState label="Loading matching summary" />;
  if (state.status === "error") return <SafeErrorState error={state.error} onRetry={() => setReloadKey((v) => v + 1)} />;
  if (state.status !== "success") return <EmptyState title="Matching unavailable" message="No safe matching summary was returned." />;
  const metrics = matchingMetrics(state.data.results);
  return <div className="page-stack">
    <section className="page-heading"><div><Link className="back-link" to={`/documents/${encodeURIComponent(state.data.document.document_id)}`}><ArrowLeft size={16} /> Document</Link><span className="eyebrow">Entity matching</span><h2>{state.data.document.filename}</h2><p>{state.data.document.document_id}</p></div><ReadOnlyNotice /></section>
    <section className="status-grid">
      <StatusCard label="Match status" value={metrics.status} detail="Highest-ranked result" icon={<ScanSearch size={18} />} />
      <StatusCard label="Confidence" value={metrics.confidence} detail="Highest available score" icon={<FileSearch size={18} />} />
      <StatusCard label="Matched entity" value={metrics.entity} detail="Safe candidate reference" icon={<Users size={18} />} />
      <StatusCard label="Candidates" value={String(metrics.count)} detail="Current API result" />
    </section>
    <section className="content-section"><div className="section-heading"><div><span className="eyebrow">Candidates</span><h2>Match results</h2></div></div>{state.data.results.length ? <DataTable caption="Matching candidates" columns={COLUMNS} rows={state.data.results} rowKey={(row) => row.match_id} /> : <EmptyState title="No matching candidates" message="The API returned no safe matching records for this document." />}</section>
  </div>;
}
