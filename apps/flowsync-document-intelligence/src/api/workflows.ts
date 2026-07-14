import type { DocumentIntelligenceApiClient } from "./client";
import { API_ENDPOINTS } from "./endpoints";
import type { WorkflowListQuery, WorkflowRunSummary } from "../types/workflow";
import { parseWorkflowRunSummary } from "../types/workflow";
import { ApiClientError } from "./errors";

export async function listWorkflowRuns(client: DocumentIntelligenceApiClient, query: WorkflowListQuery = {}) {
  const envelope = await client.get<unknown>(API_ENDPOINTS.workflowRuns, { ...query });
  if (!Array.isArray(envelope.data)) throw ApiClientError.invalidResponse(envelope.request_id);
  const data = envelope.data.map(parseWorkflowRunSummary);
  if (data.some((item) => item === null)) throw ApiClientError.invalidResponse(envelope.request_id);
  return { ...envelope, data: data as WorkflowRunSummary[] };
}
