"""Read-only matching result routes."""

from fastapi import APIRouter, Query, Request

from ..contracts import DEFAULT_PAGE_SIZE, MAX_PAGE_SIZE
from ..providers import local_provider
from ..responses import paginated_response
from .documents import _require_document

router = APIRouter(prefix="/api/v1")


@router.get("/documents/{document_id}/matching")
def get_matching(document_id: str, request: Request, limit: int = Query(DEFAULT_PAGE_SIZE, ge=1, le=MAX_PAGE_SIZE), offset: int = Query(0, ge=0)) -> dict[str, object]:
    _require_document(document_id)
    return paginated_response(local_provider.list_matching(document_id), request_id=request.state.request_id, limit=limit, offset=offset)
