"""Read-only safe audit projection routes."""

from fastapi import APIRouter, Query, Request

from ..contracts import AUDIT_EVENT_TYPES, DEFAULT_PAGE_SIZE, MAX_PAGE_SIZE
from ..auth import authorize_read
from ..providers import local_provider
from ..responses import paginated_response
from .documents import _validate_filter
from src.security import Permission

router = APIRouter(prefix="/api/v1")


@router.get("/audit-events")
def list_audit_events(request: Request, event_type: str | None = None, limit: int = Query(DEFAULT_PAGE_SIZE, ge=1, le=MAX_PAGE_SIZE), offset: int = Query(0, ge=0)) -> dict[str, object]:
    scope = authorize_read(request, Permission.AUDIT_READ, resource_type="audit_event_collection")
    _validate_filter("event_type", event_type, AUDIT_EVENT_TYPES)
    return paginated_response(local_provider.list_audit_events(event_type=event_type, tenant_id=scope.tenant_id), request_id=request.state.request_id, limit=limit, offset=offset)
