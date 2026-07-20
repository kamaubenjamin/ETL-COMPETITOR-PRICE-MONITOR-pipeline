import type { JsonScalar, JsonValue } from "./api";

export type WorkflowPermission =
  | "workflow:read" | "workflow:create" | "workflow:edit" | "workflow:test"
  | "workflow:approve" | "workflow:publish" | "workflow:deactivate" | "workflow:admin";

export interface WorkflowReference { workflow_id: string; version_id: string; version: string | number; }
export interface WorkflowOwnership { created_by: string; updated_by: string; }

export interface WorkflowDefinitionSummary {
  workflow_id: string; name: string; description: string; business_domain: string;
  document_type: string | null; status: string;
  current_draft_reference: WorkflowReference | null;
  active_published_reference: WorkflowReference | null;
  created_at: string; updated_at: string; ownership: WorkflowOwnership; revision: number;
}

export interface WorkflowChangeSummary { summary: string; changed_fields: string[]; }
export interface ConditionLeaf { field_path: string; operator: string; value?: JsonScalar | JsonScalar[]; null_policy?: string; }
export interface ConditionGroup { operator: "all" | "any" | "not"; conditions: WorkflowCondition[]; }
export type WorkflowCondition = ConditionLeaf | ConditionGroup;

export interface WorkflowAction {
  action_id: string; action_type: string; operation_name: string; operation_version: string;
  source_path?: string; target_path?: string; arguments?: Record<string, JsonScalar | JsonScalar[]>;
  error_policy?: string; output_policy?: string; enabled?: boolean;
}

export interface WorkflowRule {
  rule_id: string; name: string; stage: string; description?: string; dependencies?: string[];
  order: number; enabled?: boolean; skip?: boolean; condition?: WorkflowCondition | null;
  actions: WorkflowAction[]; input_contract_hints?: string[]; output_contract_hints?: string[];
  error_policy?: string;
}

export interface ValidationIssue {
  code: string; severity: "info" | "warning" | "error" | "blocking";
  layer: string; summary: string; rule_id: string | null; action_id: string | null; path: string | null;
}

export interface WorkflowValidation {
  structurally_valid: boolean; dependency_valid: boolean; issues: ValidationIssue[];
  ordered_rule_ids: string[]; preview_eligible: boolean; publication_eligible: boolean;
  blocked_reason_codes: string[]; version_status?: string; revision?: number;
}

export interface WorkflowVersion {
  workflow_id: string; version_id: string; version: string | number; status: string;
  derived_from_version_id: string | null; change_summary: WorkflowChangeSummary;
  authored_by: string; reviewed_by: string | null; approved_by: string | null;
  created_at: string; updated_at: string; published_at: string | null; revision: number;
  rules?: WorkflowRule[]; validation_state: WorkflowValidation | null; preview_state: string;
}

export interface WorkflowOperationArgument { name: string; value_type: string; required: boolean; default: JsonValue; description: string; }
export interface WorkflowOperation {
  name: string; version: string; category: string; description: string; availability: string;
  preview_eligible: boolean; publication_eligible: boolean; required_features: string[];
  arguments: WorkflowOperationArgument[];
}

export interface WorkflowAuditEvent {
  event_type: string; workflow_id: string; version_id: string | null; publication_id: string | null;
  actor_label: string; status: string; reason_code: string; timestamp: string; correlation_id: string | null;
}

export interface WorkflowPreviewIssue { code: string; summary: string; rule_id?: string | null; }
export interface WorkflowPreviewResult {
  preview_id: string; workflow_id: string; version_id: string; status: string;
  rules: Array<Record<string, JsonValue>>; stages: Array<Record<string, JsonValue>>;
  trace: Array<Record<string, JsonValue>>; output: Record<string, JsonValue> | null;
  issues: WorkflowPreviewIssue[];
}

export interface CreateWorkflowRequest {
  workflow_id: string; name: string; description: string; business_domain: string;
  document_type?: string; change_summary: string; rules: WorkflowRule[];
}

export interface ReplaceDraftRequest { expected_revision: number; change_summary: string; rules: WorkflowRule[]; }
export interface PreviewRequest { inline_sample?: Record<string, JsonScalar>; fixture_reference?: { fixture_id: string; label: string }; options?: { allow_redacted_values: boolean }; }
