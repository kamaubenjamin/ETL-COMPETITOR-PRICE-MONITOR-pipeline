import { ArrowLeft, Save, ShieldCheck } from "lucide-react";
import { useEffect, useState } from "react";
import { Link, useParams } from "react-router-dom";
import { createApiClient } from "../api/client";
import { LoadingState } from "../components/LoadingState";
import { SafeErrorState } from "../components/SafeErrorState";
import { OperationCatalogPanel } from "../components/workflows/OperationCatalogPanel";
import { PreviewPanel } from "../components/workflows/PreviewPanel";
import { RuleEditor } from "../components/workflows/RuleEditor";
import { ValidationPanel } from "../components/workflows/ValidationPanel";
import { getWorkflowVersion, listWorkflowOperations, replaceWorkflowDraft, testWorkflowVersion, validateWorkflowVersion } from "../services/workflowStudioApi";
import { isRequestFailure, toRequestFailure, type RequestState } from "../state/requestState";
import { canUseWorkflowAction } from "../state/workflowPermissions";
import type { JsonScalar } from "../types/api";
import type { PreviewRequest, WorkflowOperation, WorkflowPreviewResult, WorkflowRule, WorkflowValidation, WorkflowVersion } from "../types/workflowStudio";

type EditorData = { version: WorkflowVersion; operations: WorkflowOperation[] };

export function WorkflowEditorPage() {
  const { workflowId = "", versionId = "" } = useParams();
  const [reloadKey, setReloadKey] = useState(0);
  const [state, setState] = useState<RequestState<EditorData>>({ status: "loading" });
  const [rules, setRules] = useState<WorkflowRule[]>([]);
  const [changeSummary, setChangeSummary] = useState("");
  const [validation, setValidation] = useState<WorkflowValidation | null>(null);
  const [preview, setPreview] = useState<WorkflowPreviewResult | null>(null);
  const [sample, setSample] = useState<Record<string, JsonScalar>>({ document_type: "invoice" });
  const [busy, setBusy] = useState<string | null>(null);
  const [feedback, setFeedback] = useState<string | null>(null);

  useEffect(() => {
    let active = true; setState({ status: "loading" });
    const client = createApiClient();
    Promise.all([getWorkflowVersion(client, workflowId, versionId), listWorkflowOperations(client)]).then(([version, operations]) => {
      if (!active || !version.data) return;
      setRules(version.data.rules ?? []); setChangeSummary(version.data.change_summary.summary);
      setValidation(version.data.validation_state); setState({ status: "success", data: { version: version.data, operations: operations.data ?? [] } });
    }).catch((error) => { if (active) setState(toRequestFailure(error)); });
    return () => { active = false; };
  }, [workflowId, versionId, reloadKey]);

  if (state.status === "loading") return <LoadingState label="Loading structured workflow editor" />;
  if (isRequestFailure(state)) return <SafeErrorState error={state.error} onRetry={() => setReloadKey((value) => value + 1)} />;
  if (state.status !== "success") return null;
  const { version, operations } = state.data;
  const editable = version.status === "draft" && canUseWorkflowAction("workflow:edit");
  const run = async (name: string, operation: () => Promise<unknown>, message: string) => { if (busy) return; setBusy(name); setFeedback(null); try { await operation(); setFeedback(message); } catch (error) { setFeedback(toRequestFailure(error).error.message); } finally { setBusy(null); } };
  const save = () => run("save", async () => { await replaceWorkflowDraft(createApiClient(), workflowId, versionId, { expected_revision: version.revision, change_summary: changeSummary, rules }); setReloadKey((value) => value + 1); }, "Draft saved through the API.");
  const validate = () => run("validate", async () => { const result = await validateWorkflowVersion(createApiClient(), workflowId, versionId); if (result.data) setValidation(result.data); }, "Validation completed without executing the workflow.");
  const test = (request: PreviewRequest) => run("preview", async () => { const result = await testWorkflowVersion(createApiClient(), workflowId, versionId, request); if (result.data) setPreview(result.data); }, "Preview request completed.");

  return <div className="page-stack workflow-editor-page">
    <section className="page-heading document-detail-heading"><div><Link className="back-link" to={`/workflows/${encodeURIComponent(workflowId)}`}><ArrowLeft size={15} /> Workflow detail</Link><span className="eyebrow">Structured draft editor</span><h2>Version {version.version}</h2><p>Full safe replacement with optimistic revision {version.revision}. No raw code or executable expressions.</p></div><div className="read-only-notice"><ShieldCheck size={16} /> API validation is authoritative</div></section>
    {!editable ? <div className="preview-unavailable"><ShieldCheck size={18} /><div><strong>This version is immutable or edit permission is unavailable.</strong><p>No edit controls can overwrite approved or published history.</p></div></div> : null}
    {feedback ? <div className="workflow-feedback" role="status">{feedback}</div> : null}
    <section className="content-section"><div className="section-heading"><div><span className="eyebrow">Change control</span><h2>Draft replacement</h2></div><button className="primary-button" type="button" disabled={!editable || busy !== null || !changeSummary.trim()} onClick={save}><Save size={16} /> {busy === "save" ? "Saving…" : "Save draft"}</button></div><label className="workflow-wide-field">Change summary<input value={changeSummary} maxLength={1024} disabled={!editable} onChange={(event) => setChangeSummary(event.target.value)} /></label></section>
    <section className={`content-section ${!editable ? "editor-readonly" : ""}`}><div className="section-heading"><div><span className="eyebrow">Rules and actions</span><h2>Structured definition</h2></div><span className="result-summary">{rules.length} / 100 rules</span></div><RuleEditor rules={rules} operations={operations} onChange={editable ? setRules : () => undefined} /></section>
    <section className="workflow-editor-grid"><div className="content-section"><div className="section-heading"><div><span className="eyebrow">Deterministic checks</span><h2>Validation</h2></div><button className="secondary-button compact-button" type="button" disabled={!canUseWorkflowAction("workflow:edit") || busy !== null} onClick={validate}>{busy === "validate" ? "Validating…" : "Validate"}</button></div><ValidationPanel result={validation} /></div><div className="content-section"><div className="section-heading"><div><span className="eyebrow">Safe bounded test</span><h2>Preview</h2></div></div><PreviewPanel result={preview} sample={sample} onSampleChange={setSample} onRun={test} busy={busy === "preview"} allowed={canUseWorkflowAction("workflow:test")} /></div></section>
    <section className="content-section"><div className="section-heading"><div><span className="eyebrow">Catalog authority</span><h2>Operation reference</h2></div></div><OperationCatalogPanel operations={operations} compact /></section>
  </div>;
}
