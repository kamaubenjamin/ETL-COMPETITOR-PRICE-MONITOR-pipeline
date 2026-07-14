import type { DocumentIntelligenceApiClient } from "./client";
import { API_ENDPOINTS } from "./endpoints";
import type { WorkflowListQuery, WorkflowRunSummary } from "../types/workflow";

export function listWorkflowRuns(client: DocumentIntelligenceApiClient, query: WorkflowListQuery = {}) {
  return client.get<WorkflowRunSummary[]>(API_ENDPOINTS.workflowRuns, { ...query });
}

