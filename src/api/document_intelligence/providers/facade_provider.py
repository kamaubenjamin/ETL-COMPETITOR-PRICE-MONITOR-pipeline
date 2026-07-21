"""Adapter from Workflow Query Facade read models to v0.9 API provider shapes."""

from __future__ import annotations

from collections.abc import Callable, Mapping
from typing import Any, TypeVar

from src.workflow_runtime.query_facade import (
    AuditEventQuery,
    DocumentQuery,
    InMemoryWorkflowQueryFacade,
    MAX_PAGE_LIMIT,
    PageRequest,
    PageResult,
    QueryFacadeError,
    ReviewCaseQuery,
    WorkflowQueryFacadePort,
    WorkflowRunQuery,
)

from ..errors import DocumentIntelligenceAPIError


Record = dict[str, Any]
T = TypeVar("T")

_SYNTHETIC_LINEAGE = {"source_type": "synthetic_fixture", "source_name": "fictional-purchase-order-demo", "ingestion_id": "synthetic-ingestion-001", "pipeline_run_id": "synthetic-run-001", "extraction_rule": "purchase_order_v1", "page_count": 1, "line_number": None}
_SYNTHETIC_PURCHASE_ORDER: Record = {
    "document_type": "purchase_order", "purchase_order_number": "PO-FICTION-2042",
    "buyer": "Northstar Example Markets Ltd", "supplier": "Fictional Meridian Supply Co", "ship_to": "Example Distribution Centre",
    "order_date": "2026-07-10", "delivery_date": "2026-07-18", "currency": "KES",
    "subtotal": "400.00", "tax": "64.00", "total": "464.00",
    "line_items": [
        {"item_code": "DEMO-A10", "barcode": "9900000000011", "description": "Fictional archive cartons with reinforced handles", "unit": "CTN", "quantity": "2.00", "unit_price": "125.00", "net_amount": "250.00", "source_lineage": {**_SYNTHETIC_LINEAGE, "line_number": 1}},
        {"item_code": "DEMO-B20", "barcode": "9900000000028", "description": "Fictional document sleeves", "unit": "PKT", "quantity": "4.00", "unit_price": "37.50", "net_amount": "150.00", "source_lineage": {**_SYNTHETIC_LINEAGE, "line_number": 2}},
    ],
    "terms": "Fictional demonstration terms: delivery during example business hours.", "source_lineage": _SYNTHETIC_LINEAGE,
    "validation": {"status": "valid", "is_valid": True, "tolerance": "0.01", "findings": [], "checks": {"purchase_order_number_present": True, "order_date_valid": True, "delivery_date_valid": True, "delivery_not_before_order": True, "line_items_present": True, "item_codes_unique": True, "subtotal_matches_lines": True, "total_matches_subtotal_and_tax": True, "currency_valid": True}},
    "extraction_warnings": [],
}


def synthetic_purchase_order() -> Record:
    """Return an isolated copy through JSON-compatible container copying."""
    return {**_SYNTHETIC_PURCHASE_ORDER, "line_items": [{**item, "source_lineage": dict(item["source_lineage"])} for item in _SYNTHETIC_PURCHASE_ORDER["line_items"]], "source_lineage": dict(_SYNTHETIC_LINEAGE), "validation": {**_SYNTHETIC_PURCHASE_ORDER["validation"], "findings": [], "checks": dict(_SYNTHETIC_PURCHASE_ORDER["validation"]["checks"])}, "extraction_warnings": []}


def _api_error(error: QueryFacadeError) -> DocumentIntelligenceAPIError:
    status_codes = {
        "invalid_query": 400,
        "not_found": 404,
        "source_unavailable": 503,
        "internal_error": 500,
    }
    details = {"field": error.field} if error.field is not None else None
    return DocumentIntelligenceAPIError(
        error.code,
        error.message,
        status_code=status_codes[error.code],
        details=details,
    )


def _all_pages(read: Callable[[PageRequest], PageResult[T]]) -> tuple[T, ...]:
    try:
        items: list[T] = []
        offset = 0
        while True:
            page = read(PageRequest(limit=MAX_PAGE_LIMIT, offset=offset))
            items.extend(page.items)
            if len(items) >= page.total:
                return tuple(items)
            if not page.items:
                raise QueryFacadeError("internal_error")
            offset += len(page.items)
    except QueryFacadeError as error:
        raise _api_error(error) from None


class FacadeDocumentIntelligenceProvider:
    """Read-only API provider backed only by the facade public contract."""

    def __init__(self, facade: WorkflowQueryFacadePort, *, tenant_slug_aliases: Mapping[str, str] | None = None) -> None:
        if not isinstance(facade, WorkflowQueryFacadePort):
            raise ValueError("facade must implement WorkflowQueryFacadePort")
        aliases = dict(tenant_slug_aliases or {})
        if any(
            not isinstance(name, str)
            or not 1 <= len(name) <= 63
            or name[0] not in "abcdefghijklmnopqrstuvwxyz0123456789"
            or any(char not in "abcdefghijklmnopqrstuvwxyz0123456789-" for char in name)
            or not isinstance(target, str) or not target or len(target) > 128
            for name, target in aliases.items()
        ):
            raise ValueError("tenant_slug_aliases must contain bounded slugs and targets")
        self._facade = facade
        self._tenant_slug_aliases = aliases

    def _tenant_keys(self, tenant_id: str | None, tenant_slug: str | None) -> tuple[str | None, ...]:
        keys: list[str | None] = [tenant_id]
        if tenant_id is not None and tenant_slug is not None:
            target = self._tenant_slug_aliases.get(tenant_slug)
            if target is not None and target not in keys:
                keys.append(target)
        return tuple(keys)

    def list_documents(self, *, status: str | None = None, document_type: str | None = None, tenant_id: str | None = None, tenant_slug: str | None = None) -> list[Record]:
        models = []
        seen: set[str] = set()
        for tenant_key in self._tenant_keys(tenant_id, tenant_slug):
            query = DocumentQuery(status=status, document_type=document_type, tenant_id=tenant_key)
            for model in _all_pages(lambda page: self._facade.list_documents(query, page)):
                if model.document_id not in seen:
                    seen.add(model.document_id)
                    models.append(model)
        return [
            {
                "document_id": model.document_id,
                "filename": model.filename,
                "document_type": model.document_type,
                "status": model.status,
                "confidence": model.confidence,
                "current_stage": model.current_stage,
                "received_at": model.received_at,
            }
            for model in models
        ]

    def get_document(self, document_id: str, *, tenant_id: str | None = None, tenant_slug: str | None = None) -> Record | None:
        model = None
        for tenant_key in self._tenant_keys(tenant_id, tenant_slug):
            try:
                model = self._facade.get_document(document_id) if tenant_key is None else self._facade.get_document(document_id, tenant_id=tenant_key)
                break
            except QueryFacadeError as exc:
                if exc.code != "not_found":
                    raise _api_error(exc) from None
        if model is None:
            return None
        return {
            "document_id": model.document_id,
            "filename": model.filename,
            "document_type": model.document_type,
            "status": model.status,
            "confidence": model.confidence,
            "current_stage": model.current_stage,
            "received_at": model.received_at,
        }

    def list_processing(self, document_id: str, *, tenant_id: str | None = None, tenant_slug: str | None = None) -> list[Record]:
        if self.get_document(document_id, tenant_id=tenant_id, tenant_slug=tenant_slug) is None:
            return []
        models = _all_pages(lambda page: self._facade.list_processing(document_id, page))
        return [{"stage": model.stage, "status": model.status, "occurred_at": model.occurred_at} for model in models]

    def list_validation(self, document_id: str, *, tenant_id: str | None = None, tenant_slug: str | None = None) -> list[Record]:
        if self.get_document(document_id, tenant_id=tenant_id, tenant_slug=tenant_slug) is None:
            return []
        models = _all_pages(lambda page: self._facade.list_validation_issues(document_id, page))
        return [
            {
                "issue_id": model.issue_id,
                "severity": model.severity,
                "field": model.field,
                "rule_id": model.rule_id,
                "code": model.code,
                "message": model.message,
            }
            for model in models
        ]

    def list_matching(self, document_id: str, *, tenant_id: str | None = None, tenant_slug: str | None = None) -> list[Record]:
        if self.get_document(document_id, tenant_id=tenant_id, tenant_slug=tenant_slug) is None:
            return []
        models = _all_pages(lambda page: self._facade.list_matching_results(document_id, page))
        return [
            {
                "match_id": model.match_id,
                "entity_type": model.entity_type,
                "candidate_id": model.candidate_id,
                "confidence": model.confidence,
                "status": model.status,
            }
            for model in models
        ]

    def get_purchase_order(self, document_id: str, *, tenant_id: str | None = None, tenant_slug: str | None = None) -> Record | None:
        """Return the bounded fictional result for the existing synthetic PO record."""
        document = self.get_document(document_id, tenant_id=tenant_id, tenant_slug=tenant_slug)
        if document is None or document.get("document_type") != "purchase_order" or document_id != "doc-002":
            return None
        return synthetic_purchase_order()

    def list_review_cases(self, *, status: str | None = None, priority: str | None = None, tenant_id: str | None = None) -> list[Record]:
        query = ReviewCaseQuery(status=status, priority=priority)
        models = _all_pages(lambda page: self._facade.list_review_cases(query, page))
        return [self._review_case(model) for model in models if self._document_visible(model.document_id, tenant_id)]

    def get_review_case(self, review_case_id: str, *, tenant_id: str | None = None) -> Record | None:
        try:
            model = self._facade.get_review_case(review_case_id)
        except QueryFacadeError as exc:
            if exc.code == "not_found":
                return None
            raise _api_error(exc) from None
        return self._review_case(model) if self._document_visible(model.document_id, tenant_id) else None

    def _document_visible(self, document_id: str | None, tenant_id: str | None) -> bool:
        if tenant_id is None:
            return True
        if document_id is None:
            return False
        return self.get_document(document_id, tenant_id=tenant_id) is not None

    @staticmethod
    def _review_case(model: Any) -> Record:
        return {
            "review_case_id": model.review_case_id,
            "document_id": model.document_id,
            "reason_code": model.reason_code,
            "priority": model.priority,
            "status": model.status,
            "assigned_reviewer": model.assigned_reviewer_id,
            "correction_count": model.correction_count,
            "decision_code": model.decision_code,
            "reprocess_state": model.reprocess_state,
            "created_at": model.created_at,
        }

    def list_corrections(self, review_case_id: str, *, tenant_id: str | None = None) -> list[Record]:
        if self.get_review_case(review_case_id, tenant_id=tenant_id) is None:
            return []
        models = _all_pages(lambda page: self._facade.list_correction_history(review_case_id, page))
        return [model.to_dict() for model in models]

    def list_reprocess_plans(self, *, tenant_id: str | None = None) -> list[Record]:
        models = _all_pages(lambda page: self._facade.list_reprocess_plans(None, page))
        return [
            model.to_dict()
            for model in models
            if self.get_review_case(model.review_case_id, tenant_id=tenant_id) is not None
        ]

    def list_workflow_runs(self, *, status: str | None = None, tenant_id: str | None = None) -> list[Record]:
        query = WorkflowRunQuery(status=status, tenant_id=tenant_id)
        models = _all_pages(lambda page: self._facade.list_workflow_runs(query, page))
        return [
            {
                "run_id": model.run_id,
                "workflow_name": model.workflow_name,
                "status": model.status,
                "started_at": model.started_at,
                "duration_ms": model.duration_ms,
            }
            for model in models
        ]

    def list_audit_events(self, *, event_type: str | None = None, tenant_id: str | None = None) -> list[Record]:
        query = AuditEventQuery(event_type=event_type)
        models = _all_pages(lambda page: self._facade.list_audit_events(query, page))
        return [
            {
                "event_id": model.event_id,
                "event_type": model.event_type,
                "actor_id": model.actor_id,
                "document_id": model.document_id,
                "review_case_id": model.review_case_id,
                "occurred_at": model.occurred_at,
                "metadata": dict(model.metadata),
            }
            for model in models
            if self._document_visible(model.document_id, tenant_id)
        ]


facade_provider = FacadeDocumentIntelligenceProvider(InMemoryWorkflowQueryFacade())
uat_read_only_facade_provider = FacadeDocumentIntelligenceProvider(
    InMemoryWorkflowQueryFacade(),
    tenant_slug_aliases={"flowsync-uat": "tenant-uat"},
)
