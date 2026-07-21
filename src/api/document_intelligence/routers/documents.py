"""Read-only document inbox and processing routes."""

from fastapi import APIRouter, Query, Request

from ..contracts import DEFAULT_PAGE_SIZE, DOCUMENT_STATUSES, DOCUMENT_TYPES, MAX_PAGE_SIZE
from ..auth import authorize_read
from ..errors import DocumentIntelligenceAPIError
from ..providers import get_document_intelligence_provider
from ..responses import paginated_response, success_response
from src.security import Permission

router = APIRouter(prefix="/api/v1")


def _validate_filter(name: str, value: str | None, allowed: frozenset[str]) -> None:
    if value is not None and value not in allowed:
        raise DocumentIntelligenceAPIError("invalid_filter", "Query filter is invalid.", details={"field": name})


def _require_document(document_id: str, request: Request, *, tenant_id: str | None = None, tenant_slug: str | None = None) -> dict[str, object]:
    document = get_document_intelligence_provider(request).get_document(document_id, tenant_id=tenant_id, tenant_slug=tenant_slug)
    if document is None:
        raise DocumentIntelligenceAPIError("document_not_found", "Document was not found.", status_code=404)
    return document


@router.get("/documents")
def list_documents(request: Request, status: str | None = None, document_type: str | None = None, limit: int = Query(DEFAULT_PAGE_SIZE, ge=1, le=MAX_PAGE_SIZE), offset: int = Query(0, ge=0)) -> dict[str, object]:
    scope = authorize_read(request, Permission.DOCUMENT_LIST, resource_type="document_collection")
    _validate_filter("status", status, DOCUMENT_STATUSES)
    _validate_filter("document_type", document_type, DOCUMENT_TYPES)
    rows = get_document_intelligence_provider(request).list_documents(status=status, document_type=document_type, tenant_id=scope.tenant_id, tenant_slug=scope.tenant_slug)
    return paginated_response(rows, request_id=request.state.request_id, limit=limit, offset=offset)


@router.get("/documents/{document_id}")
def get_document(document_id: str, request: Request) -> dict[str, object]:
    scope = authorize_read(request, Permission.DOCUMENT_READ, resource_type="document", resource_id=document_id, conceal_unauthorized_resource=True)
    return success_response(_require_document(document_id, request, tenant_id=scope.tenant_id, tenant_slug=scope.tenant_slug), request_id=request.state.request_id)


@router.get("/documents/{document_id}/purchase-order")
def get_purchase_order(document_id: str, request: Request) -> dict[str, object]:
    scope = authorize_read(request, Permission.DOCUMENT_READ, resource_type="document", resource_id=document_id, conceal_unauthorized_resource=True)
    _require_document(document_id, request, tenant_id=scope.tenant_id, tenant_slug=scope.tenant_slug)
    result = get_document_intelligence_provider(request).get_purchase_order(document_id, tenant_id=scope.tenant_id, tenant_slug=scope.tenant_slug)
    if result is None:
        raise DocumentIntelligenceAPIError("purchase_order_not_found", "Purchase-order result was not found.", status_code=404)
    return success_response(result, request_id=request.state.request_id)


@router.get("/documents/{document_id}/processing")
def get_processing(document_id: str, request: Request, limit: int = Query(DEFAULT_PAGE_SIZE, ge=1, le=MAX_PAGE_SIZE), offset: int = Query(0, ge=0)) -> dict[str, object]:
    scope = authorize_read(request, Permission.DOCUMENT_READ, resource_type="document", resource_id=document_id, conceal_unauthorized_resource=True)
    _require_document(document_id, request, tenant_id=scope.tenant_id, tenant_slug=scope.tenant_slug)
    return paginated_response(get_document_intelligence_provider(request).list_processing(document_id, tenant_id=scope.tenant_id, tenant_slug=scope.tenant_slug), request_id=request.state.request_id, limit=limit, offset=offset)
