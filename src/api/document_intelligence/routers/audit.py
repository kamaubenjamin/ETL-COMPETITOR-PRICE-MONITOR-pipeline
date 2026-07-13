"""Read-only safe audit projection routes."""

from fastapi import APIRouter, Query, Request

from ..contracts import AUDIT_EVENT_TYPES, DEFAULT_PAGE_SIZE, MAX_PAGE_SIZE
from ..providers import local_provider
from ..responses import paginated_response
from .documents import _validate_filter

router = APIRouter(prefix="/api/v1")


@router.get("/audit-events")
def list_audit_events(request: Request, event_type: str | None = None, limit: int = Query(DEFAULT_PAGE_SIZE, ge=1, le=MAX_PAGE_SIZE), offset: int = Query(0, ge=0)) -> dict[str, object]:
    _validate_filter("event_type", event_type, AUDIT_EVENT_TYPES)
    return paginated_response(local_provider.list_audit_events(event_type=event_type), request_id=request.state.request_id, limit=limit, offset=offset)
