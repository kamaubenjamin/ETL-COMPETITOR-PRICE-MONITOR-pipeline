"""Read-only workflow run routes."""

from fastapi import APIRouter, Query, Request

from ..contracts import DEFAULT_PAGE_SIZE, MAX_PAGE_SIZE, WORKFLOW_STATUSES
from ..auth import authorize_read
from ..providers import get_document_intelligence_provider
from ..responses import paginated_response
from .documents import _validate_filter
from src.security import Permission

router = APIRouter(prefix="/api/v1")


@router.get("/workflow-runs")
def list_workflow_runs(request: Request, status: str | None = None, limit: int = Query(DEFAULT_PAGE_SIZE, ge=1, le=MAX_PAGE_SIZE), offset: int = Query(0, ge=0)) -> dict[str, object]:
    scope = authorize_read(request, Permission.WORKFLOW_READ, resource_type="workflow_run_collection")
    _validate_filter("status", status, WORKFLOW_STATUSES)
    return paginated_response(get_document_intelligence_provider(request).list_workflow_runs(status=status, tenant_id=scope.tenant_id), request_id=request.state.request_id, limit=limit, offset=offset)
