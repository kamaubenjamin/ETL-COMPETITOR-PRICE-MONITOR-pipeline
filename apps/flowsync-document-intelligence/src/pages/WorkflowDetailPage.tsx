import { Archive, ArrowLeft, CheckCircle2, FilePlus2, PauseCircle, Rocket, Send, ShieldCheck } from "lucide-react";
import { useEffect, useState } from "react";
import { Link, useParams } from "react-router-dom";
import { createApiClient } from "../api/client";
import { LoadingState } from "../components/LoadingState";
import { SafeErrorState } from "../components/SafeErrorState";
import { StatusChip } from "../components/StatusChip";
import { OperationCatalogPanel } from "../components/workflows/OperationCatalogPanel";
import { approveWorkflowVersion, archiveWorkflow, createWorkflowVersion, deactivateWorkflow, getWorkflowDefinition, listWorkflowAudit, listWorkflowOperations, listWorkflowVersions, publishWorkflowVersion, submitWorkflowVersion } from "../services/workflowStudioApi";
import { formatDateTime } from "../state/documentViewModels";
import { isRequestFailure, toRequestFailure, type RequestState } from "../state/requestState";
import { canUseWorkflowAction } from "../state/workflowPermissions";
import type { WorkflowAuditEvent, WorkflowDefinitionSummary, WorkflowOperation, WorkflowVersion } from "../types/workflowStudio";

type DetailData = { definition: WorkflowDefinitionSummary; versions: WorkflowVersion[]; audit: WorkflowAuditEvent[]; operations: WorkflowOperation[] };
type DetailTab = "overview" | "versions" | "operations" | "audit";

export function WorkflowDetailPage() {
  const { workflowId = "" } = useParams();
  const [tab, setTab] = useState<DetailTab>("overview");
  const [reloadKey, setReloadKey] = useState(0);
  const [state, setState] = useState<RequestState<DetailData>>({ status: "loading" });
  const [busy, setBusy] = useState<string | null>(null);
  const [feedback, setFeedback] = useState<string | null>(null);

  useEffect(() => {
    let active = true; setState({ status: "loading" });
    const client = createApiClient();
    Promise.all([getWorkflowDefinition(client, workflowId), listWorkflowVersions(client, workflowId, { limit: 100, offset: 0 }), listWorkflowAudit(client, workflowId, { limit: 100, offset: 0 }), listWorkflowOperations(client)]).then(([definition, versions, audit, operations]) => {
      if (active && definition.data) setState({ status: "success", data: { definition: definition.data, versions: versions.data ?? [], audit: audit.data ?? [], operations: operations.data ?? [] } });
    }).catch((error) => { if (active) setState(toRequestFailure(error)); });
    return () => { active = false; };
  }, [workflowId, reloadKey]);

  if (state.status === "loading") return <LoadingState label="Loading workflow definition" />;
  if (isRequestFailure(state)) return <SafeErrorState error={state.error} onRetry={() => setReloadKey((value) => value + 1)} />;
  if (state.status !== "success") return null;
  const { definition, versions, audit, operations } = state.data;
  const currentDraft = versions.find((version) => version.version_id === definition.current_draft_reference?.version_id);

  const action = async (name: string, operation: () => Promise<unknown>, success: string, confirmation: string) => {
    if (!window.confirm(confirmation) || busy) return;
    setBusy(name); setFeedback(null);
    try { await operation(); setFeedback(success); setReloadKey((value) => value + 1); }
    catch (error) { setFeedback(toRequestFailure(error).error.message); }
    finally { setBusy(null); }
  };
  const newDraft = () => action("new-draft", () => createWorkflowVersion(createApiClient(), workflowId, { change_summary: "New governed draft.", ...(definition.active_published_reference ? { source_version_id: definition.active_published_reference.version_id } : {}) }), "A new draft was created from API-governed history.", "Create a new editable draft? Immutable source history will be preserved.");

  return <div className="page-stack workflow-detail-page">
    <section className="page-heading document-detail-heading"><div><Link className="back-link" to="/workflows"><ArrowLeft size={15} /> Business Workflows</Link><span className="eyebrow">Governed definition</span><h2>{definition.name}</h2><p>{definition.description || "No description supplied."}</p></div><div className="read-only-notice"><ShieldCheck size={16} /> Published definition governance only</div></section>
    <section className="workflow-detail-summary"><div><span>Workflow ID</span><strong>{definition.workflow_id}</strong></div><div><span>Status</span><StatusChip status={definition.status} /></div><div><span>Current draft</span><strong>{definition.current_draft_reference?.version ?? "None"}</strong></div><div><span>Active publication</span><strong>{definition.active_published_reference?.version ?? "None"}</strong></div><div><span>Updated</span><strong>{formatDateTime(definition.updated_at)}</strong></div></section>
    <nav className="detail-tabs" aria-label="Workflow sections">{(["overview", "versions", "operations", "audit"] as DetailTab[]).map((value) => <button className={`detail-tab ${tab === value ? "detail-tab--active" : ""}`} type="button" key={value} onClick={() => setTab(value)}>{value}</button>)}</nav>
    {feedback ? <div className="workflow-feedback" role="status">{feedback}</div> : null}
    {tab === "overview" ? <><section className="content-section"><div className="section-heading"><div><span className="eyebrow">Lifecycle controls</span><h2>Governance actions</h2></div></div><div className="lifecycle-grid">
      <button type="button" disabled={!canUseWorkflowAction("workflow:edit") || Boolean(currentDraft) || busy !== null} onClick={newDraft}><FilePlus2 size={17} /><strong>Create draft</strong><span>Preserve lineage</span></button>
      <button type="button" disabled={!canUseWorkflowAction("workflow:edit") || currentDraft?.status !== "test_passed" || busy !== null} onClick={() => currentDraft && action("submit", () => submitWorkflowVersion(createApiClient(), workflowId, currentDraft.version_id), "Draft submitted for review.", "Submit this tested draft for approval review?")}><Send size={17} /><strong>Submit</strong><span>Enter approval review</span></button>
      <button type="button" disabled={!canUseWorkflowAction("workflow:approve") || currentDraft?.status !== "test_passed" || busy !== null} onClick={() => currentDraft && action("approve", () => approveWorkflowVersion(createApiClient(), workflowId, currentDraft.version_id, currentDraft.revision), "Draft approved by the API.", "Approve this validated and tested definition? Author/reviewer separation is enforced by the API.")}><CheckCircle2 size={17} /><strong>Approve</strong><span>Evidence required</span></button>
      <button type="button" disabled={!canUseWorkflowAction("workflow:publish") || currentDraft?.status !== "approved" || busy !== null} onClick={() => currentDraft && action("publish", () => publishWorkflowVersion(createApiClient(), workflowId, currentDraft.version_id, currentDraft.revision, definition.revision), "Published definition governance only. Production execution activation is not enabled.", "Published definition governance only. Production execution activation is not enabled. Continue?")}><Rocket size={17} /><strong>Publish</strong><span>Governance only</span></button>
      <button type="button" disabled={!canUseWorkflowAction("workflow:deactivate") || !definition.active_published_reference || busy !== null} onClick={() => action("deactivate", () => deactivateWorkflow(createApiClient(), workflowId, 1, definition.revision), "Publication deactivated. No previous version was automatically activated.", "Deactivate the active publication? No previous version will be auto-activated.")}><PauseCircle size={17} /><strong>Deactivate</strong><span>No fallback activation</span></button>
      <button type="button" disabled={!canUseWorkflowAction("workflow:admin") || Boolean(definition.active_published_reference) || busy !== null} onClick={() => action("archive", () => archiveWorkflow(createApiClient(), workflowId, definition.revision), "Workflow archived. Immutable history was preserved.", "Archive this workflow? Immutable version and audit history will be preserved.")}><Archive size={17} /><strong>Archive</strong><span>History preserved</span></button>
    </div><p className="permission-hint">Controls reflect known permission labels for usability only. The API remains authoritative for every action.</p></section><section className="content-section"><div className="section-heading"><div><span className="eyebrow">Definition context</span><h2>Overview</h2></div></div><dl className="metadata-grid"><div><dt>Business domain</dt><dd>{definition.business_domain}</dd></div><div><dt>Document type</dt><dd>{definition.document_type ?? "Not constrained"}</dd></div><div><dt>Created by</dt><dd>{definition.ownership.created_by}</dd></div><div><dt>Updated by</dt><dd>{definition.ownership.updated_by}</dd></div></dl></section></> : null}
    {tab === "versions" ? <section className="content-section"><div className="section-heading"><div><span className="eyebrow">Immutable history</span><h2>Versions</h2></div></div><div className="version-list">{versions.map((version) => <article key={version.version_id}><div><strong>Version {version.version}</strong><small>{version.version_id}</small></div><StatusChip status={version.status} /><div><span>{version.change_summary.summary}</span><small>By {version.authored_by} · {formatDateTime(version.updated_at)}</small></div><div>{version.status === "draft" && canUseWorkflowAction("workflow:edit") ? <Link className="secondary-button compact-button" to={`/workflows/${encodeURIComponent(workflowId)}/versions/${encodeURIComponent(version.version_id)}/edit`}>Open draft</Link> : <span className="immutable-label">Immutable</span>}</div></article>)}</div></section> : null}
    {tab === "operations" ? <section className="content-section"><div className="section-heading"><div><span className="eyebrow">API operation catalog</span><h2>Available and planned operations</h2></div></div><OperationCatalogPanel operations={operations} /></section> : null}
    {tab === "audit" ? <section className="content-section"><div className="section-heading"><div><span className="eyebrow">Safe audit intents</span><h2>Audit history</h2></div></div>{audit.length ? <ol className="workflow-audit-list">{audit.map((event, index) => <li key={`${event.event_type}-${event.timestamp}-${index}`}><span className="timeline-marker"><ShieldCheck size={15} /></span><div><strong>{event.event_type}</strong><span>{event.reason_code} · {event.status}</span><small>{event.actor_label} · {formatDateTime(event.timestamp)}{event.correlation_id ? ` · ${event.correlation_id}` : ""}</small></div><div><small>{event.version_id ? `Version ${event.version_id}` : "Definition"}</small>{event.publication_id ? <small>Publication {event.publication_id}</small> : null}</div></li>)}</ol> : <div className="workflow-empty-panel"><span>No audit events are available.</span></div>}</section> : null}
  </div>;
}
