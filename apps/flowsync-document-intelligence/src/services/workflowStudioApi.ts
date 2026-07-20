import type { DocumentIntelligenceApiClient } from "../api/client";
import { API_ENDPOINTS } from "../api/endpoints";
import type { ApiEnvelope, ListQuery } from "../types/api";
import type {
  CreateWorkflowRequest, PreviewRequest, ReplaceDraftRequest, WorkflowAuditEvent,
  WorkflowDefinitionSummary, WorkflowOperation, WorkflowPreviewResult, WorkflowValidation, WorkflowVersion,
} from "../types/workflowStudio";

export const listWorkflowDefinitions = (client: DocumentIntelligenceApiClient, query: ListQuery = {}): Promise<ApiEnvelope<WorkflowDefinitionSummary[]>> => client.get(API_ENDPOINTS.workflowDefinitions, { limit: query.limit, offset: query.offset });
export const getWorkflowDefinition = (client: DocumentIntelligenceApiClient, workflowId: string): Promise<ApiEnvelope<WorkflowDefinitionSummary>> => client.get(API_ENDPOINTS.workflowDefinition(workflowId));
export const listWorkflowVersions = (client: DocumentIntelligenceApiClient, workflowId: string, query: ListQuery = {}): Promise<ApiEnvelope<WorkflowVersion[]>> => client.get(API_ENDPOINTS.workflowVersions(workflowId), { limit: query.limit, offset: query.offset });
export const getWorkflowVersion = (client: DocumentIntelligenceApiClient, workflowId: string, versionId: string): Promise<ApiEnvelope<WorkflowVersion>> => client.get(API_ENDPOINTS.workflowVersion(workflowId, versionId));
export const listWorkflowAudit = (client: DocumentIntelligenceApiClient, workflowId: string, query: ListQuery = {}): Promise<ApiEnvelope<WorkflowAuditEvent[]>> => client.get(API_ENDPOINTS.workflowAudit(workflowId), { limit: query.limit, offset: query.offset });
export const listWorkflowOperations = (client: DocumentIntelligenceApiClient): Promise<ApiEnvelope<WorkflowOperation[]>> => client.get(API_ENDPOINTS.workflowOperations);
export const createWorkflow = (client: DocumentIntelligenceApiClient, payload: CreateWorkflowRequest) => client.mutate<{ definition: WorkflowDefinitionSummary; version: WorkflowVersion }>(API_ENDPOINTS.workflowDefinitions, "POST", payload);
export const createWorkflowVersion = (client: DocumentIntelligenceApiClient, workflowId: string, payload: { change_summary: string; source_version_id?: string }) => client.mutate<WorkflowVersion>(API_ENDPOINTS.workflowVersions(workflowId), "POST", payload);
export const replaceWorkflowDraft = (client: DocumentIntelligenceApiClient, workflowId: string, versionId: string, payload: ReplaceDraftRequest) => client.mutate<WorkflowVersion>(API_ENDPOINTS.workflowVersion(workflowId, versionId), "PATCH", payload);
export const validateWorkflowVersion = (client: DocumentIntelligenceApiClient, workflowId: string, versionId: string) => client.mutate<WorkflowValidation>(API_ENDPOINTS.workflowValidate(workflowId, versionId), "POST");
export const testWorkflowVersion = (client: DocumentIntelligenceApiClient, workflowId: string, versionId: string, payload: PreviewRequest) => client.mutate<WorkflowPreviewResult>(API_ENDPOINTS.workflowTest(workflowId, versionId), "POST", payload);
export const submitWorkflowVersion = (client: DocumentIntelligenceApiClient, workflowId: string, versionId: string) => client.mutate<Record<string, unknown>>(API_ENDPOINTS.workflowSubmit(workflowId, versionId), "POST");
export const approveWorkflowVersion = (client: DocumentIntelligenceApiClient, workflowId: string, versionId: string, expectedRevision: number) => client.mutate<WorkflowVersion>(API_ENDPOINTS.workflowApprove(workflowId, versionId), "POST", { expected_revision: expectedRevision });
export const publishWorkflowVersion = (client: DocumentIntelligenceApiClient, workflowId: string, versionId: string, versionRevision: number, definitionRevision: number) => client.mutate<Record<string, unknown>>(API_ENDPOINTS.workflowPublish(workflowId, versionId), "POST", { expected_version_revision: versionRevision, expected_definition_revision: definitionRevision, supersede_previous: true });
export const deactivateWorkflow = (client: DocumentIntelligenceApiClient, workflowId: string, publicationRevision: number, definitionRevision: number) => client.mutate<Record<string, unknown>>(API_ENDPOINTS.workflowDeactivate(workflowId), "POST", { expected_publication_revision: publicationRevision, expected_definition_revision: definitionRevision });
export const archiveWorkflow = (client: DocumentIntelligenceApiClient, workflowId: string, definitionRevision: number) => client.mutate<Record<string, unknown>>(API_ENDPOINTS.workflowArchive(workflowId), "POST", { expected_definition_revision: definitionRevision });
