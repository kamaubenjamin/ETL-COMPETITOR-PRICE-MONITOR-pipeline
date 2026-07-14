"""Read-only validation issue routes."""

from fastapi import APIRouter, Query, Request

from ..contracts import DEFAULT_PAGE_SIZE, MAX_PAGE_SIZE
from ..auth import authorize_read
from ..providers import get_document_intelligence_provider
from ..responses import paginated_response
from .documents import _require_document
from src.security import Permission

router = APIRouter(prefix="/api/v1")


@router.get("/documents/{document_id}/validation")
def get_validation(document_id: str, request: Request, limit: int = Query(DEFAULT_PAGE_SIZE, ge=1, le=MAX_PAGE_SIZE), offset: int = Query(0, ge=0)) -> dict[str, object]:
    scope = authorize_read(request, Permission.DOCUMENT_READ, resource_type="document", resource_id=document_id, conceal_unauthorized_resource=True)
    _require_document(document_id, request, tenant_id=scope.tenant_id)
    return paginated_response(get_document_intelligence_provider(request).list_validation(document_id, tenant_id=scope.tenant_id), request_id=request.state.request_id, limit=limit, offset=offset)
