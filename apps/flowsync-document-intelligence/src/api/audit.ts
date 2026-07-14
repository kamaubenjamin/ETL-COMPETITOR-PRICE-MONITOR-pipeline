import type { DocumentIntelligenceApiClient } from "./client";
import { API_ENDPOINTS } from "./endpoints";
import type { AuditEventSummary, AuditListQuery } from "../types/audit";
import { parseAuditEventSummary } from "../types/audit";
import { ApiClientError } from "./errors";

export async function listAuditEvents(client: DocumentIntelligenceApiClient, query: AuditListQuery = {}) {
  const envelope = await client.get<unknown>(API_ENDPOINTS.auditEvents, { ...query });
  if (!Array.isArray(envelope.data)) throw ApiClientError.invalidResponse(envelope.request_id);
  const data = envelope.data.map(parseAuditEventSummary);
  if (data.some((item) => item === null)) throw ApiClientError.invalidResponse(envelope.request_id);
  return { ...envelope, data: data as AuditEventSummary[] };
}
