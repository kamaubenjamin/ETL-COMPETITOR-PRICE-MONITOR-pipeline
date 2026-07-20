import type { WorkflowPermission } from "../types/workflowStudio";

const CATALOG = new Set<WorkflowPermission>([
  "workflow:read", "workflow:create", "workflow:edit", "workflow:test",
  "workflow:approve", "workflow:publish", "workflow:deactivate", "workflow:admin",
]);

let effectiveHints = new Set<WorkflowPermission>();

if (import.meta.env.DEV) {
  const configured = import.meta.env.VITE_WORKFLOW_STUDIO_PERMISSIONS ?? "workflow:read";
  effectiveHints = new Set(configured.split(",").map((value) => value.trim()).filter(
    (value): value is WorkflowPermission => CATALOG.has(value as WorkflowPermission),
  ));
}

export function configureWorkflowPermissionHints(values: readonly string[]): void {
  effectiveHints = new Set(values.filter(
    (value): value is WorkflowPermission => CATALOG.has(value as WorkflowPermission),
  ));
}

export function knownWorkflowPermissions(): ReadonlySet<WorkflowPermission> {
  return new Set(effectiveHints);
}

export function canUseWorkflowAction(permission: WorkflowPermission): boolean {
  return knownWorkflowPermissions().has(permission);
}
