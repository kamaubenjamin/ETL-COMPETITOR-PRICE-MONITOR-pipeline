import type { DocumentIntelligenceApiClient } from "./client";
import { API_ENDPOINTS } from "./endpoints";
import type { AuditEventSummary, AuditListQuery } from "../types/audit";

export function listAuditEvents(client: DocumentIntelligenceApiClient, query: AuditListQuery = {}) {
  return client.get<AuditEventSummary[]>(API_ENDPOINTS.auditEvents, { ...query });
}

