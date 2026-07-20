import { CircleCheck, CircleSlash } from "lucide-react";
import { StatusChip } from "../StatusChip";
import type { WorkflowOperation } from "../../types/workflowStudio";

export function OperationCatalogPanel({ operations, compact = false }: { operations: readonly WorkflowOperation[]; compact?: boolean }) {
  if (!operations.length) return <p className="workflow-muted">No operation descriptors are available.</p>;
  return <div className={compact ? "operation-grid operation-grid--compact" : "operation-grid"}>
    {operations.map((operation) => <article className={`operation-card ${operation.availability !== "available" ? "operation-card--unavailable" : ""}`} key={`${operation.name}:${operation.version}`}>
      <div className="operation-card-heading">
        <span className="operation-icon">{operation.availability === "available" ? <CircleCheck size={16} /> : <CircleSlash size={16} />}</span>
        <div><strong>{operation.name}</strong><small>v{operation.version} · {operation.category}</small></div>
        <StatusChip status={operation.availability} />
      </div>
      <p>{operation.description}</p>
      <div className="eligibility-row"><span>Preview: {operation.preview_eligible ? "Eligible" : "Blocked"}</span><span>Publication: {operation.publication_eligible ? "Eligible" : "Blocked"}</span></div>
      {operation.arguments.length ? <ul className="operation-arguments">{operation.arguments.map((argument) => <li key={argument.name}><strong>{argument.name}{argument.required ? " *" : ""}</strong><span>{argument.value_type} · {argument.description || "No description"}</span></li>)}</ul> : null}
      {operation.required_features.length ? <small>Requires {operation.required_features.join(", ")}</small> : null}
    </article>)}
  </div>;
}
