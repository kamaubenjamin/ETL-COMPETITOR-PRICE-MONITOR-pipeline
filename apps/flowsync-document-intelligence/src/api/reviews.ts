import type { DocumentIntelligenceApiClient } from "./client";
import { API_ENDPOINTS } from "./endpoints";
import type {
  CorrectionSummary,
  ReprocessPlanSummary,
  ReviewCaseSummary,
  ReviewListQuery,
} from "../types/review";
import { parseCorrectionSummary, parseReprocessPlanSummary, parseReviewCaseSummary } from "../types/review";
import { ApiClientError } from "./errors";
import type { ApiEnvelope } from "../types/api";

function mapList<T>(envelope: ApiEnvelope<unknown>, parser: (value: unknown) => T | null): ApiEnvelope<T[]> {
  if (!Array.isArray(envelope.data)) throw ApiClientError.invalidResponse(envelope.request_id);
  const data = envelope.data.map(parser);
  if (data.some((item) => item === null)) throw ApiClientError.invalidResponse(envelope.request_id);
  return { ...envelope, data: data as T[] };
}

export async function listReviewCases(client: DocumentIntelligenceApiClient, query: ReviewListQuery = {}) {
  return mapList(await client.get<unknown>(API_ENDPOINTS.reviewCases, { ...query }), parseReviewCaseSummary);
}

export async function getReviewCase(client: DocumentIntelligenceApiClient, reviewCaseId: string) {
  const envelope = await client.get<unknown>(API_ENDPOINTS.reviewCase(reviewCaseId));
  const data = parseReviewCaseSummary(envelope.data);
  if (!data) throw ApiClientError.invalidResponse(envelope.request_id);
  return { ...envelope, data } as ApiEnvelope<ReviewCaseSummary>;
}

export async function listCorrectionHistory(client: DocumentIntelligenceApiClient, reviewCaseId: string) {
  return mapList(await client.get<unknown>(API_ENDPOINTS.corrections(reviewCaseId)), parseCorrectionSummary);
}

export async function listReprocessPlans(client: DocumentIntelligenceApiClient) {
  return mapList(await client.get<unknown>(API_ENDPOINTS.reprocessPlans), parseReprocessPlanSummary);
}
