import type { DocumentIntelligenceApiClient } from "./client";
import { API_ENDPOINTS } from "./endpoints";
import type {
  DocumentListQuery,
  DocumentSummary,
  MatchingResult,
  ProcessingStatus,
  ValidationIssue,
} from "../types/document";
import {
  parseDocumentSummary,
  parseMatchingResult,
  parseProcessingStatus,
  parseValidationIssue,
} from "../types/document";
import { ApiClientError } from "./errors";
import type { ApiEnvelope } from "../types/api";

function mapEnvelopeList<T>(
  envelope: ApiEnvelope<unknown>,
  parser: (value: unknown) => T | null,
): ApiEnvelope<T[]> {
  if (!Array.isArray(envelope.data)) {
    throw ApiClientError.invalidResponse(envelope.request_id);
  }
  const data = envelope.data.map(parser);
  if (data.some((item) => item === null)) {
    throw ApiClientError.invalidResponse(envelope.request_id);
  }
  return { ...envelope, data: data as T[] };
}

export async function listDocuments(client: DocumentIntelligenceApiClient, query: DocumentListQuery = {}) {
  const envelope = await client.get<unknown>(API_ENDPOINTS.documents, { ...query });
  return mapEnvelopeList<DocumentSummary>(envelope, parseDocumentSummary);
}

export async function getDocument(client: DocumentIntelligenceApiClient, documentId: string) {
  const envelope = await client.get<unknown>(API_ENDPOINTS.document(documentId));
  const data = parseDocumentSummary(envelope.data);
  if (!data) throw ApiClientError.invalidResponse(envelope.request_id);
  return { ...envelope, data } as ApiEnvelope<DocumentSummary>;
}

export async function getDocumentProcessing(client: DocumentIntelligenceApiClient, documentId: string) {
  const envelope = await client.get<unknown>(API_ENDPOINTS.processing(documentId));
  return mapEnvelopeList<ProcessingStatus>(envelope, parseProcessingStatus);
}

export async function getDocumentValidation(client: DocumentIntelligenceApiClient, documentId: string) {
  const envelope = await client.get<unknown>(API_ENDPOINTS.validation(documentId));
  return mapEnvelopeList<ValidationIssue>(envelope, parseValidationIssue);
}

export async function getDocumentMatching(client: DocumentIntelligenceApiClient, documentId: string) {
  const envelope = await client.get<unknown>(API_ENDPOINTS.matching(documentId));
  return mapEnvelopeList<MatchingResult>(envelope, parseMatchingResult);
}
