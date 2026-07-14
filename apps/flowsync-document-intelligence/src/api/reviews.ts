import type { DocumentIntelligenceApiClient } from "./client";
import { API_ENDPOINTS } from "./endpoints";
import type {
  CorrectionSummary,
  ReprocessPlanSummary,
  ReviewCaseSummary,
  ReviewListQuery,
} from "../types/review";

export function listReviewCases(client: DocumentIntelligenceApiClient, query: ReviewListQuery = {}) {
  return client.get<ReviewCaseSummary[]>(API_ENDPOINTS.reviewCases, { ...query });
}

export function getReviewCase(client: DocumentIntelligenceApiClient, reviewCaseId: string) {
  return client.get<ReviewCaseSummary>(API_ENDPOINTS.reviewCase(reviewCaseId));
}

export function listCorrectionHistory(client: DocumentIntelligenceApiClient, reviewCaseId: string) {
  return client.get<CorrectionSummary[]>(API_ENDPOINTS.corrections(reviewCaseId));
}

export function listReprocessPlans(client: DocumentIntelligenceApiClient) {
  return client.get<ReprocessPlanSummary[]>(API_ENDPOINTS.reprocessPlans);
}

