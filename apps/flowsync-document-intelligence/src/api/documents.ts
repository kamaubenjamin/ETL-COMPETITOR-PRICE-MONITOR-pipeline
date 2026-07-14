import type { DocumentIntelligenceApiClient } from "./client";
import { API_ENDPOINTS } from "./endpoints";
import type {
  DocumentListQuery,
  DocumentSummary,
  MatchingResult,
  ProcessingStatus,
  ValidationIssue,
} from "../types/document";

export function listDocuments(client: DocumentIntelligenceApiClient, query: DocumentListQuery = {}) {
  return client.get<DocumentSummary[]>(API_ENDPOINTS.documents, { ...query });
}

export function getDocument(client: DocumentIntelligenceApiClient, documentId: string) {
  return client.get<DocumentSummary>(API_ENDPOINTS.document(documentId));
}

export function getDocumentProcessing(client: DocumentIntelligenceApiClient, documentId: string) {
  return client.get<ProcessingStatus[]>(API_ENDPOINTS.processing(documentId));
}

export function getDocumentValidation(client: DocumentIntelligenceApiClient, documentId: string) {
  return client.get<ValidationIssue[]>(API_ENDPOINTS.validation(documentId));
}

export function getDocumentMatching(client: DocumentIntelligenceApiClient, documentId: string) {
  return client.get<MatchingResult[]>(API_ENDPOINTS.matching(documentId));
}

