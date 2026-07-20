import { Plus, ShieldCheck, Workflow } from "lucide-react";
import { FormEvent, useEffect, useState } from "react";
import { Link, useLocation, useNavigate } from "react-router-dom";
import { createApiClient } from "../api/client";
import { AccessScopeNotice } from "../components/AccessScopeNotice";
import { EmptyState } from "../components/EmptyState";
import { LoadingState } from "../components/LoadingState";
import { SafeErrorState } from "../components/SafeErrorState";
import { StatusChip } from "../components/StatusChip";
import { createWorkflow, listWorkflowDefinitions } from "../services/workflowStudioApi";
import { formatDateTime } from "../state/documentViewModels";
import { isRequestFailure, toRequestFailure, type RequestState } from "../state/requestState";
import { canUseWorkflowAction } from "../state/workflowPermissions";
import type { WorkflowDefinitionSummary } from "../types/workflowStudio";

const PAGE_SIZE = 25;

export function WorkflowStudioPage() {
  const navigate = useNavigate();
  const location = useLocation();
  const [offset, setOffset] = useState(0);
  const [reloadKey, setReloadKey] = useState(0);
  const [state, setState] = useState<RequestState<WorkflowDefinitionSummary[]>>({ status: "loading" });
  const [total, setTotal] = useState(0);
  const [creating, setCreating] = useState(location.pathname.endsWith("/new"));
  const [submitting, setSubmitting] = useState(false);
  const [createError, setCreateError] = useState<ReturnType<typeof toRequestFailure> | null>(null);
  const canCreate = canUseWorkflowAction("workflow:create");

  useEffect(() => {
    let active = true;
    setState({ status: "loading" });
    listWorkflowDefinitions(createApiClient(), { limit: PAGE_SIZE, offset }).then((result) => {
      if (!active) return;
      const data = result.data ?? [];
      setTotal(result.metadata.pagination?.total ?? data.length);
      setState(data.length ? { status: "success", data } : { status: "empty" });
    }).catch((error) => { if (active) setState(toRequestFailure(error)); });
    return () => { active = false; };
  }, [offset, reloadKey]);

  const submitCreate = async (event: FormEvent<HTMLFormElement>) => {
    event.preventDefault();
    if (!canCreate || submitting) return;
    const form = new FormData(event.currentTarget);
    setSubmitting(true); setCreateError(null);
    try {
      const result = await createWorkflow(createApiClient(), {
        workflow_id: String(form.get("workflow_id") ?? ""), name: String(form.get("name") ?? ""),
        description: String(form.get("description") ?? ""), business_domain: String(form.get("business_domain") ?? ""),
        document_type: String(form.get("document_type") ?? "") || undefined,
        change_summary: String(form.get("change_summary") ?? "Initial governed draft."), rules: [],
      });
      if (result.data) navigate(`/workflows/${encodeURIComponent(result.data.definition.workflow_id)}`);
    } catch (error) { setCreateError(toRequestFailure(error)); }
    finally { setSubmitting(false); }
  };

  return <div className="page-stack workflow-studio-page">
    <section className="page-heading"><div><span className="eyebrow">Governed definition workspace</span><h2>Business Workflows</h2><p>Author and govern structured workflow definitions through the API-authoritative Studio boundary.</p></div><div className="read-only-notice"><ShieldCheck size={16} /> API authority preserved · runtime activation disabled</div></section>
    <AccessScopeNotice />
    <section className="workflow-summary-strip"><div><Workflow size={18} /><span><strong>{total}</strong> workflow definitions in the current API scope</span></div><button className="primary-button" type="button" disabled={!canCreate} onClick={() => setCreating((value) => !value)}><Plus size={16} /> Create workflow</button></section>
    {!canCreate ? <p className="permission-hint">Create is hidden or disabled unless `workflow:create` is known. The API always makes the final authorization decision.</p> : null}
    {creating ? <section className="content-section workflow-form-card"><div className="section-heading"><div><span className="eyebrow">New governed definition</span><h2>Create workflow</h2></div></div><form className="workflow-create-form" onSubmit={submitCreate}><div className="workflow-form-grid"><label>Workflow ID<input name="workflow_id" required maxLength={128} pattern="[A-Za-z0-9][A-Za-z0-9._:-]*" /></label><label>Name<input name="name" required maxLength={256} /></label><label>Business domain<input name="business_domain" required maxLength={128} /></label><label>Document type<input name="document_type" maxLength={64} /></label></div><label className="workflow-wide-field">Description<textarea name="description" maxLength={1024} /></label><label className="workflow-wide-field">Initial change summary<input name="change_summary" required maxLength={1024} defaultValue="Initial governed draft." /></label><div className="workflow-form-actions"><button className="secondary-button compact-button" type="button" onClick={() => setCreating(false)}>Cancel</button><button className="primary-button" type="submit" disabled={submitting}>{submitting ? "Creating…" : "Create safe draft"}</button></div></form>{createError ? <SafeErrorState error={createError.error} /> : null}</section> : null}
    {state.status === "loading" ? <LoadingState label="Loading workflow definitions" /> : null}
    {isRequestFailure(state) ? <SafeErrorState error={state.error} onRetry={() => setReloadKey((value) => value + 1)} /> : null}
    {state.status === "empty" ? <EmptyState title="No workflows yet" message="No governed workflow definitions are available in the current API scope." /> : null}
    {state.status === "success" ? <section className="content-section"><div className="section-heading"><div><span className="eyebrow">Definition register</span><h2>Workflow definitions</h2></div></div><div className="workflow-list-table"><div className="workflow-list-head"><span>Workflow</span><span>Domain</span><span>Status</span><span>Draft / published</span><span>Updated</span></div>{state.data.map((workflow) => <Link className="workflow-list-row" to={`/workflows/${encodeURIComponent(workflow.workflow_id)}`} key={workflow.workflow_id}><span className="workflow-name-cell"><strong>{workflow.name}</strong><small>{workflow.workflow_id}</small></span><span>{workflow.business_domain}<small>{workflow.document_type ?? "Any document type"}</small></span><span><StatusChip status={workflow.status} /></span><span><small>Draft {workflow.current_draft_reference?.version ?? "None"}</small><small>Published {workflow.active_published_reference?.version ?? "None"}</small></span><span>{formatDateTime(workflow.updated_at)}<small>{workflow.ownership.updated_by}</small></span></Link>)}</div><div className="pagination-row"><button className="secondary-button compact-button" type="button" disabled={offset === 0} onClick={() => setOffset(Math.max(0, offset - PAGE_SIZE))}>Previous</button><span>{offset + 1}–{Math.min(offset + PAGE_SIZE, total)} of {total}</span><button className="secondary-button compact-button" type="button" disabled={offset + PAGE_SIZE >= total} onClick={() => setOffset(offset + PAGE_SIZE)}>Next</button></div></section> : null}
  </div>;
}
