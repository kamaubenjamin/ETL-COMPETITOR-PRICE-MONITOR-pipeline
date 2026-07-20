import { Plus, Trash2 } from "lucide-react";
import type { JsonScalar } from "../../types/api";
import type { ConditionLeaf, WorkflowAction, WorkflowCondition, WorkflowOperation, WorkflowRule } from "../../types/workflowStudio";

const OPERATORS = ["equals", "not_equals", "contains", "exists", "not_exists", "greater_than", "less_than"];
const newLeaf = (): ConditionLeaf => ({ field_path: "document.amount", operator: "equals", value: "" });
const emptyRule = (order: number): WorkflowRule => ({ rule_id: `rule-${order + 1}`, name: "New rule", stage: "validation", description: "", dependencies: [], order, enabled: true, skip: false, condition: null, actions: [] });

function ConditionLeafFields({ condition, onChange }: { condition: ConditionLeaf; onChange: (value: ConditionLeaf) => void }) {
  const valueless = ["exists", "not_exists"].includes(condition.operator);
  return <div className="workflow-form-grid condition-leaf">
    <label>Logical path<input value={condition.field_path} maxLength={256} onChange={(event) => onChange({ ...condition, field_path: event.target.value })} /></label>
    <label>Operator<select value={condition.operator} onChange={(event) => { const operator = event.target.value; onChange({ ...condition, operator, ...(["exists", "not_exists"].includes(operator) ? { value: undefined } : {}) }); }}>{OPERATORS.map((operator) => <option key={operator}>{operator}</option>)}</select></label>
    <label>Value<input disabled={valueless} value={valueless ? "" : String(condition.value ?? "")} maxLength={256} onChange={(event) => onChange({ ...condition, value: event.target.value })} /></label>
  </div>;
}

function ConditionEditor({ condition, onChange }: { condition: WorkflowCondition; onChange: (value: WorkflowCondition) => void }) {
  const grouped = "conditions" in condition;
  const composition = grouped ? condition.operator : "single";
  const changeComposition = (value: string) => {
    if (value === "single") onChange(grouped ? (condition.conditions[0] as ConditionLeaf ?? newLeaf()) : condition);
    else onChange({ operator: value as "all" | "any", conditions: grouped ? condition.conditions : [condition, newLeaf()] });
  };
  return <div className="condition-builder">
    <label className="condition-composition">Composition<select value={composition} onChange={(event) => changeComposition(event.target.value)}><option value="single">Single condition</option><option value="all">All conditions (AND)</option><option value="any">Any condition (OR)</option></select></label>
    {grouped ? condition.conditions.map((child, index) => "field_path" in child ? <div className="condition-child" key={index}><ConditionLeafFields condition={child} onChange={(value) => onChange({ ...condition, conditions: condition.conditions.map((item, itemIndex) => itemIndex === index ? value : item) })} /><button className="icon-button" type="button" aria-label={`Remove condition ${index + 1}`} onClick={() => onChange({ ...condition, conditions: condition.conditions.filter((_, itemIndex) => itemIndex !== index) })}><Trash2 size={14} /></button></div> : null) : <ConditionLeafFields condition={condition} onChange={onChange} />}
    {grouped ? <button className="secondary-button compact-button" type="button" disabled={condition.conditions.length >= 8} onClick={() => onChange({ ...condition, conditions: [...condition.conditions, newLeaf()] })}><Plus size={14} /> Add condition</button> : null}
  </div>;
}

function ActionEditor({ action, operations, onChange, onRemove }: { action: WorkflowAction; operations: WorkflowOperation[]; onChange: (value: WorkflowAction) => void; onRemove: () => void }) {
  const selected = operations.find((item) => item.name === action.operation_name && item.version === action.operation_version);
  const setArgument = (name: string, value: JsonScalar) => onChange({ ...action, arguments: { ...(action.arguments ?? {}), [name]: value } });
  return <div className="action-block">
    <div className="action-row"><label>Action ID<input value={action.action_id} onChange={(event) => onChange({ ...action, action_id: event.target.value })} /></label><label>Operation<select value={`${action.operation_name}:${action.operation_version}`} onChange={(event) => { const operation = operations.find((item) => `${item.name}:${item.version}` === event.target.value); if (operation?.availability === "available") onChange({ ...action, action_type: operation.name, operation_name: operation.name, operation_version: operation.version, arguments: {} }); }}>{operations.map((operation) => <option key={`${operation.name}:${operation.version}`} disabled={operation.availability !== "available"} value={`${operation.name}:${operation.version}`}>{operation.name} · {operation.availability}</option>)}</select></label><label>Source path<input value={action.source_path ?? ""} onChange={(event) => onChange({ ...action, source_path: event.target.value || undefined })} /></label><button className="icon-button action-remove" type="button" aria-label={`Remove ${action.action_id}`} onClick={onRemove}><Trash2 size={15} /></button></div>
    {selected?.arguments.length ? <div className="action-arguments">{selected.arguments.map((argument) => <label key={argument.name}>{argument.name}{argument.required ? " *" : ""}<input required={argument.required} value={String(action.arguments?.[argument.name] ?? argument.default ?? "")} maxLength={256} onChange={(event) => setArgument(argument.name, event.target.value)} /><small>{argument.description || argument.value_type}</small></label>)}</div> : <p className="workflow-muted">This operation declares no configurable arguments.</p>}
  </div>;
}

export function RuleEditor({ rules, operations, onChange }: { rules: WorkflowRule[]; operations: WorkflowOperation[]; onChange: (rules: WorkflowRule[]) => void }) {
  const update = (index: number, changes: Partial<WorkflowRule>) => onChange(rules.map((rule, itemIndex) => itemIndex === index ? { ...rule, ...changes } : rule));
  const available = operations.filter((operation) => operation.availability === "available");
  return <div className="rule-editor-stack">
    {rules.map((rule, index) => <article className="rule-card" key={`${rule.rule_id}-${index}`}>
      <div className="rule-card-heading"><div><span className="eyebrow">Rule {index + 1}</span><h3>{rule.name || "Unnamed rule"}</h3></div><button className="icon-button" type="button" aria-label={`Remove ${rule.rule_id}`} onClick={() => onChange(rules.filter((_, itemIndex) => itemIndex !== index).map((item, order) => ({ ...item, order })))}><Trash2 size={16} /></button></div>
      <div className="workflow-form-grid"><label>Rule ID<input value={rule.rule_id} maxLength={128} onChange={(event) => update(index, { rule_id: event.target.value })} /></label><label>Name<input value={rule.name} maxLength={256} onChange={(event) => update(index, { name: event.target.value })} /></label><label>Stage<input value={rule.stage} maxLength={128} onChange={(event) => update(index, { stage: event.target.value })} /></label><label>Dependencies<input value={(rule.dependencies ?? []).join(", ")} placeholder="rule-1, rule-2" onChange={(event) => update(index, { dependencies: event.target.value.split(",").map((item) => item.trim()).filter(Boolean) })} /></label></div>
      <label className="workflow-wide-field">Description<textarea value={rule.description ?? ""} maxLength={1024} onChange={(event) => update(index, { description: event.target.value })} /></label>
      <div className="rule-flags"><label><input type="checkbox" checked={rule.enabled ?? true} onChange={(event) => update(index, { enabled: event.target.checked })} /> Enabled</label><label><input type="checkbox" checked={rule.skip ?? false} onChange={(event) => update(index, { skip: event.target.checked })} /> Skip</label></div>
      <section className="builder-section"><div className="builder-heading"><div><strong>Conditions</strong><span>Bounded logical paths with AND/OR composition</span></div><button className="secondary-button compact-button" type="button" onClick={() => update(index, { condition: rule.condition ? null : newLeaf() })}>{rule.condition ? "Remove" : "Add condition"}</button></div>{rule.condition ? <ConditionEditor condition={rule.condition} onChange={(condition) => update(index, { condition })} /> : <p className="workflow-muted">No condition. Actions apply whenever dependencies are satisfied.</p>}</section>
      <section className="builder-section"><div className="builder-heading"><div><strong>Actions</strong><span>Only available catalog operations can be selected</span></div><button className="secondary-button compact-button" type="button" disabled={!available.length || rule.actions.length >= 32} onClick={() => { const operation = available[0]; if (operation) update(index, { actions: [...rule.actions, { action_id: `action-${rule.actions.length + 1}`, action_type: operation.name, operation_name: operation.name, operation_version: operation.version, enabled: true }] }); }}><Plus size={14} /> Add action</button></div>{rule.actions.map((action, actionIndex) => <ActionEditor action={action} operations={operations} key={`${action.action_id}-${actionIndex}`} onChange={(value) => update(index, { actions: rule.actions.map((item, itemIndex) => itemIndex === actionIndex ? value : item) })} onRemove={() => update(index, { actions: rule.actions.filter((_, itemIndex) => itemIndex !== actionIndex) })} />)}</section>
    </article>)}
    <button className="secondary-button add-rule-button" type="button" disabled={rules.length >= 100} onClick={() => onChange([...rules, emptyRule(rules.length)])}><Plus size={16} /> Add structured rule</button>
  </div>;
}
