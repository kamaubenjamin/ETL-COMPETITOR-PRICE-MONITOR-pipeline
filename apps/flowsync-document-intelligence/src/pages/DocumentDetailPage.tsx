import { ArrowLeft, CheckCheck, FileSearch, History, ListChecks, ScrollText, Workflow } from "lucide-react";
import { useEffect, useState } from "react";
import { Link, useParams } from "react-router-dom";
import { createApiClient } from "../api/client";
import {
  getDocument,
  getDocumentMatching,
  getDocumentProcessing,
  getDocumentValidation,
} from "../api/documents";
import { DocumentMetadataPanel } from "../components/DocumentMetadataPanel";
import { DocumentSectionCard } from "../components/DocumentSectionCard";
import { EmptyState } from "../components/EmptyState";
import { ExportReadinessPanel } from "../components/ExportReadinessPanel";
import { LoadingState } from "../components/LoadingState";
import { ProcessingStatusPanel } from "../components/ProcessingStatusPanel";
import { SafeErrorState } from "../components/SafeErrorState";
import { StatusChip } from "../components/StatusChip";
import { toDocumentDetailViewModel } from "../state/documentViewModels";
import { isRequestFailure, malformedRequestState, notFoundRequestState, toRequestFailure, type RequestState } from "../state/requestState";
import type { DocumentDetailViewModel } from "../types/viewModels";

export function DocumentDetailPage() {
  const { documentId } = useParams<{ documentId: string }>();
  const [reloadKey, setReloadKey] = useState(0);
  const [state, setState] = useState<RequestState<DocumentDetailViewModel>>({ status: "loading" });

  useEffect(() => {
    let active = true;
    setState({ status: "loading" });

    const load = async () => {
      if (!documentId) {
        setState(notFoundRequestState());
        return;
      }
      try {
        const client = createApiClient();
        const [document, processing, validation, matching] = await Promise.all([
          getDocument(client, documentId),
          getDocumentProcessing(client, documentId),
          getDocumentValidation(client, documentId),
          getDocumentMatching(client, documentId),
        ]);
        if (!active) return;
        if (!document.data || !processing.data || !validation.data || !matching.data) {
          setState(malformedRequestState(document.request_id));
          return;
        }
        setState({
          status: "success",
          data: toDocumentDetailViewModel(document.data, processing.data, validation.data, matching.data),
        });
      } catch (error) {
        if (active) setState(toRequestFailure(error));
      }
    };
    void load();
    return () => { active = false; };
  }, [documentId, reloadKey]);

  if (state.status === "loading") return <LoadingState label="Loading document detail" />;
  if (isRequestFailure(state)) return <SafeErrorState error={state.error} onRetry={() => setReloadKey((value) => value + 1)} />;
  if (state.status === "empty" || state.status === "idle") {
    return <EmptyState title="Document detail is unavailable" message="No safe document metadata was returned." />;
  }

  const document = state.data;
  return (
    <div className="page-stack">
      <section className="page-heading document-detail-heading">
        <div>
          <Link className="back-link" to="/documents"><ArrowLeft size={16} aria-hidden="true" /> Documents</Link>
          <span className="eyebrow">Document detail</span>
          <h2>{document.filename}</h2>
          <p>{document.id}</p>
        </div>
        <StatusChip status={document.status} label={document.statusLabel} />
      </section>

      <nav className="detail-tabs" aria-label="Document sections">
        <Link className="detail-tab detail-tab--active" to={`/documents/${encodeURIComponent(document.id)}`}>Overview</Link>
        <a className="detail-tab" href="#processing">Processing</a>
        <Link className="detail-tab" to={`/documents/${encodeURIComponent(document.id)}/validation`}>Validation</Link>
        <Link className="detail-tab" to={`/documents/${encodeURIComponent(document.id)}/matching`}>Matching</Link>
        <span className="detail-tab detail-tab--disabled" aria-disabled="true">Review</span>
        <span className="detail-tab detail-tab--disabled" aria-disabled="true">Workflow</span>
        <span className="detail-tab detail-tab--disabled" aria-disabled="true">Audit</span>
      </nav>

      <DocumentMetadataPanel document={document} />

      <section className="document-section-grid" aria-label="Document summaries">
        <DocumentSectionCard title="Validation" value={String(document.validationIssueCount)} detail={`${document.validationErrorCount} error issue${document.validationErrorCount === 1 ? "" : "s"}`} icon={<ListChecks size={20} />} />
        <DocumentSectionCard title="Matching" value={String(document.matchingResultCount)} detail={`Highest confidence: ${document.highestMatchConfidence}`} icon={<FileSearch size={20} />} />
        <DocumentSectionCard title="Review" value="Not available" detail="Review summary is deferred" icon={<CheckCheck size={20} />} />
        <DocumentSectionCard title="Workflow" value="Not available" detail="Workflow correlation is deferred" icon={<Workflow size={20} />} />
        <DocumentSectionCard title="Audit" value="Not available" detail="Document audit correlation is deferred" icon={<ScrollText size={20} />} />
      </section>

      <ExportReadinessPanel documentId={document.id} />

      <ProcessingStatusPanel documentId={document.id} />

      <section className="processing-section" id="processing" aria-labelledby="processing-heading">
        <div className="section-heading">
          <div><span className="eyebrow">Lifecycle</span><h2 id="processing-heading">Processing history</h2></div>
          <span className="read-only-label">Read-only</span>
        </div>
        {document.processing.length === 0 ? (
          <EmptyState title="No processing history" message="No safe processing events were returned for this document." />
        ) : (
          <ol className="processing-timeline">
            {document.processing.map((item, index) => (
              <li key={`${item.stage}-${item.occurredAt}-${index}`}>
                <div className="timeline-marker"><History size={15} aria-hidden="true" /></div>
                <div><strong>{item.stage}</strong><span>{item.occurredAt}</span></div>
                <StatusChip status={item.status} />
              </li>
            ))}
          </ol>
        )}
      </section>
    </div>
  );
}
