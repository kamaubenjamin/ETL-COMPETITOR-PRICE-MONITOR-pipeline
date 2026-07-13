"""Read-only document inbox and processing routes."""

from fastapi import APIRouter, Query, Request

from ..contracts import DEFAULT_PAGE_SIZE, DOCUMENT_STATUSES, DOCUMENT_TYPES, MAX_PAGE_SIZE
from ..errors import DocumentIntelligenceAPIError
from ..providers import local_provider
from ..responses import paginated_response, success_response

router = APIRouter(prefix="/api/v1")


def _validate_filter(name: str, value: str | None, allowed: frozenset[str]) -> None:
    if value is not None and value not in allowed:
        raise DocumentIntelligenceAPIError("invalid_filter", "Query filter is invalid.", details={"field": name})


def _require_document(document_id: str) -> dict[str, object]:
    document = local_provider.get_document(document_id)
    if document is None:
        raise DocumentIntelligenceAPIError("document_not_found", "Document was not found.", status_code=404)
    return document


@router.get("/documents")
def list_documents(request: Request, status: str | None = None, document_type: str | None = None, limit: int = Query(DEFAULT_PAGE_SIZE, ge=1, le=MAX_PAGE_SIZE), offset: int = Query(0, ge=0)) -> dict[str, object]:
    _validate_filter("status", status, DOCUMENT_STATUSES)
    _validate_filter("document_type", document_type, DOCUMENT_TYPES)
    rows = local_provider.list_documents(status=status, document_type=document_type)
    return paginated_response(rows, request_id=request.state.request_id, limit=limit, offset=offset)


@router.get("/documents/{document_id}")
def get_document(document_id: str, request: Request) -> dict[str, object]:
    return success_response(_require_document(document_id), request_id=request.state.request_id)


@router.get("/documents/{document_id}/processing")
def get_processing(document_id: str, request: Request, limit: int = Query(DEFAULT_PAGE_SIZE, ge=1, le=MAX_PAGE_SIZE), offset: int = Query(0, ge=0)) -> dict[str, object]:
    _require_document(document_id)
    return paginated_response(local_provider.list_processing(document_id), request_id=request.state.request_id, limit=limit, offset=offset)
