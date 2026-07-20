import { EyeOff, Info } from "lucide-react";
import { useState } from "react";
import type { JsonScalar, JsonValue } from "../../types/api";
import type { PreviewRequest, WorkflowPreviewResult } from "../../types/workflowStudio";

function SafeRecord({ value }: { value: Record<string, JsonValue> }) {
  return <dl className="preview-record">{Object.entries(value).slice(0, 50).map(([key, item]) => <div key={key}><dt>{key}</dt><dd>{typeof item === "object" ? "Structured value" : String(item)}</dd></div>)}</dl>;
}

export function PreviewPanel({ result, sample, onSampleChange, onRun, busy, allowed }: {
  result: WorkflowPreviewResult | null; sample: Record<string, JsonScalar>;
  onSampleChange: (value: Record<string, JsonScalar>) => void; onRun: (request: PreviewRequest) => void; busy: boolean; allowed: boolean;
}) {
  const [source, setSource] = useState<"inline" | "approved">("inline");
  const [fixtureId, setFixtureId] = useState("");
  const [fixtureLabel, setFixtureLabel] = useState("");
  const entries = Object.entries(sample);
  const update = (index: number, key: string, value: string) => {
    const next = entries.map(([currentKey, currentValue], itemIndex) => itemIndex === index ? [key, value] : [currentKey, currentValue]);
    onSampleChange(Object.fromEntries(next.filter(([name]) => name)));
  };
  return <div className="preview-stack">
    <div className="workflow-empty-panel"><Info size={18} /><div><strong>Bounded preview input</strong><p>Use scalar key/value fields or an approved fixture reference. API validation remains authoritative.</p></div></div>
    <div className="preview-source-tabs"><button type="button" className={source === "inline" ? "preview-source-active" : ""} onClick={() => setSource("inline")}>Inline safe sample</button><button type="button" className={source === "approved" ? "preview-source-active" : ""} onClick={() => setSource("approved")}>Approved fixture reference</button></div>
    {source === "inline" ? <div className="sample-editor">{entries.map(([key, value], index) => <div className="sample-row" key={`${index}-${key}`}><input aria-label={`Sample key ${index + 1}`} value={key} maxLength={64} onChange={(event) => update(index, event.target.value, String(value ?? ""))} /><input aria-label={`Sample value ${index + 1}`} value={String(value ?? "")} maxLength={256} onChange={(event) => update(index, key, event.target.value)} /></div>)}<button className="secondary-button compact-button" type="button" disabled={entries.length >= 12} onClick={() => onSampleChange({ ...sample, [`field_${entries.length + 1}`]: "" })}>Add sample field</button></div> : <div className="workflow-form-grid"><label>Fixture ID<input value={fixtureId} maxLength={128} onChange={(event) => setFixtureId(event.target.value)} /></label><label>Safe label<input value={fixtureLabel} maxLength={128} onChange={(event) => setFixtureLabel(event.target.value)} /></label><p className="permission-hint">Only an API-approved reference is sent. FlowSync never loads or displays the fixture body.</p></div>}
    <button className="primary-button workflow-action-button" type="button" onClick={() => onRun(source === "inline" ? { inline_sample: sample, options: { allow_redacted_values: true } } : { fixture_reference: { fixture_id: fixtureId, label: fixtureLabel }, options: { allow_redacted_values: true } })} disabled={busy || !allowed || (source === "approved" && (!fixtureId || !fixtureLabel))}>{busy ? "Requesting preview…" : "Run safe preview"}</button>
    {!allowed ? <p className="permission-hint">Preview control requires known `workflow:test` permission. The API remains authoritative.</p> : null}
    {result?.status === "preview_unavailable" ? <div className="preview-unavailable" role="status"><EyeOff size={18} /><div><strong>Preview execution adapter is not connected in this environment.</strong><p>No successful execution is implied.</p></div></div> : null}
    {result && result.status !== "preview_unavailable" ? <div className="preview-result"><div className="validation-metrics"><span>Status {result.status}</span><span>{result.stages.length} stages</span><span>{result.rules.length} rules</span><span>{result.trace.length} trace events</span></div>{result.issues.map((issue) => <div className="issue-row" key={issue.code}><strong>{issue.code}</strong><span>{issue.summary}</span></div>)}{result.output ? <SafeRecord value={result.output} /> : <p className="workflow-muted">No output values were returned.</p>}</div> : null}
  </div>;
}
