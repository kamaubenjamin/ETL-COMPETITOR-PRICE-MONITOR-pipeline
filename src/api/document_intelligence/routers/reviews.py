"""Read-only review, correction, and reprocess routes."""

from fastapi import APIRouter, Query, Request

from ..contracts import DEFAULT_PAGE_SIZE, MAX_PAGE_SIZE, REVIEW_PRIORITIES, REVIEW_STATUSES
from ..auth import authorize_read
from ..errors import DocumentIntelligenceAPIError
from ..providers import get_document_intelligence_provider
from ..responses import paginated_response, success_response
from .documents import _validate_filter
from src.security import Permission

router = APIRouter(prefix="/api/v1")


def _require_review_case(review_case_id: str, request: Request, *, tenant_id: str | None = None) -> dict[str, object]:
    review_case = get_document_intelligence_provider(request).get_review_case(review_case_id, tenant_id=tenant_id)
    if review_case is None:
        raise DocumentIntelligenceAPIError("review_case_not_found", "Review case was not found.", status_code=404)
    return review_case


@router.get("/review-cases")
def list_review_cases(request: Request, status: str | None = None, priority: str | None = None, limit: int = Query(DEFAULT_PAGE_SIZE, ge=1, le=MAX_PAGE_SIZE), offset: int = Query(0, ge=0)) -> dict[str, object]:
    scope = authorize_read(request, Permission.DOCUMENT_REVIEW, resource_type="review_case_collection")
    _validate_filter("status", status, REVIEW_STATUSES)
    _validate_filter("priority", priority, REVIEW_PRIORITIES)
    rows = get_document_intelligence_provider(request).list_review_cases(status=status, priority=priority, tenant_id=scope.tenant_id)
    return paginated_response(rows, request_id=request.state.request_id, limit=limit, offset=offset)


@router.get("/review-cases/{review_case_id}")
def get_review_case(review_case_id: str, request: Request) -> dict[str, object]:
    scope = authorize_read(request, Permission.DOCUMENT_REVIEW, resource_type="review_case", resource_id=review_case_id, conceal_unauthorized_resource=True)
    return success_response(_require_review_case(review_case_id, request, tenant_id=scope.tenant_id), request_id=request.state.request_id)


@router.get("/review-cases/{review_case_id}/corrections")
def get_corrections(review_case_id: str, request: Request, limit: int = Query(DEFAULT_PAGE_SIZE, ge=1, le=MAX_PAGE_SIZE), offset: int = Query(0, ge=0)) -> dict[str, object]:
    scope = authorize_read(request, Permission.DOCUMENT_REVIEW, resource_type="review_case", resource_id=review_case_id, conceal_unauthorized_resource=True)
    _require_review_case(review_case_id, request, tenant_id=scope.tenant_id)
    return paginated_response(get_document_intelligence_provider(request).list_corrections(review_case_id, tenant_id=scope.tenant_id), request_id=request.state.request_id, limit=limit, offset=offset)


@router.get("/reprocess-plans")
def list_reprocess_plans(request: Request, limit: int = Query(DEFAULT_PAGE_SIZE, ge=1, le=MAX_PAGE_SIZE), offset: int = Query(0, ge=0)) -> dict[str, object]:
    scope = authorize_read(request, Permission.DOCUMENT_REVIEW, resource_type="reprocess_plan_collection")
    return paginated_response(get_document_intelligence_provider(request).list_reprocess_plans(tenant_id=scope.tenant_id), request_id=request.state.request_id, limit=limit, offset=offset)
