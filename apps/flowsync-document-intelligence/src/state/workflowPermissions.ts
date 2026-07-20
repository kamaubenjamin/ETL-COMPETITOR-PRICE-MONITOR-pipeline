import type { WorkflowPermission } from "../types/workflowStudio";

const CATALOG = new Set<WorkflowPermission>([
  "workflow:read", "workflow:create", "workflow:edit", "workflow:test",
  "workflow:approve", "workflow:publish", "workflow:deactivate", "workflow:admin",
]);

export function knownWorkflowPermissions(): ReadonlySet<WorkflowPermission> {
  const configured = import.meta.env.VITE_WORKFLOW_STUDIO_PERMISSIONS ?? "workflow:read";
  return new Set(configured.split(",").map((value) => value.trim()).filter(
    (value): value is WorkflowPermission => CATALOG.has(value as WorkflowPermission),
  ));
}

export function canUseWorkflowAction(permission: WorkflowPermission): boolean {
  return knownWorkflowPermissions().has(permission);
}
