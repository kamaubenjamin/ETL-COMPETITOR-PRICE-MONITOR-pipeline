import { AlertTriangle, CheckCircle2, Info } from "lucide-react";
import type { WorkflowValidation } from "../../types/workflowStudio";

export function ValidationPanel({ result }: { result: WorkflowValidation | null }) {
  if (!result) return <div className="workflow-empty-panel"><Info size={18} /><div><strong>Validation not yet run</strong><p>Validation checks structure and dependencies. It does not execute the workflow.</p></div></div>;
  const groups = ["blocking", "error", "warning", "info"] as const;
  return <div className="validation-stack">
    <div className="validation-metrics">
      <span className={result.structurally_valid ? "metric-good" : "metric-bad"}>Structural {result.structurally_valid ? "valid" : "blocked"}</span>
      <span className={result.dependency_valid ? "metric-good" : "metric-bad"}>Dependencies {result.dependency_valid ? "valid" : "blocked"}</span>
      <span>Preview {result.preview_eligible ? "eligible" : "blocked"}</span>
      <span>Publication {result.publication_eligible ? "eligible" : "blocked"}</span>
    </div>
    {result.blocked_reason_codes.length ? <div className="blocked-reasons"><AlertTriangle size={16} /><span>{result.blocked_reason_codes.join(" · ")}</span></div> : <div className="blocked-reasons blocked-reasons--clear"><CheckCircle2 size={16} /><span>No blocking reason codes returned.</span></div>}
    {groups.map((severity) => {
      const issues = result.issues.filter((issue) => issue.severity === severity);
      return issues.length ? <section className="issue-group" key={severity}><h4>{severity}</h4>{issues.map((issue, index) => <div className="issue-row" key={`${issue.code}-${index}`}><strong>{issue.code}</strong><span>{issue.summary}</span>{issue.rule_id ? <small>Rule {issue.rule_id}{issue.path ? ` · ${issue.path}` : ""}</small> : null}</div>)}</section> : null;
    })}
  </div>;
}
