"""Read-only review, correction, and reprocess routes."""

from fastapi import APIRouter, Query, Request

from ..contracts import DEFAULT_PAGE_SIZE, MAX_PAGE_SIZE, REVIEW_PRIORITIES, REVIEW_STATUSES
from ..errors import DocumentIntelligenceAPIError
from ..providers import local_provider
from ..responses import paginated_response, success_response
from .documents import _validate_filter

router = APIRouter(prefix="/api/v1")


def _require_review_case(review_case_id: str) -> dict[str, object]:
    review_case = local_provider.get_review_case(review_case_id)
    if review_case is None:
        raise DocumentIntelligenceAPIError("review_case_not_found", "Review case was not found.", status_code=404)
    return review_case


@router.get("/review-cases")
def list_review_cases(request: Request, status: str | None = None, priority: str | None = None, limit: int = Query(DEFAULT_PAGE_SIZE, ge=1, le=MAX_PAGE_SIZE), offset: int = Query(0, ge=0)) -> dict[str, object]:
    _validate_filter("status", status, REVIEW_STATUSES)
    _validate_filter("priority", priority, REVIEW_PRIORITIES)
    rows = local_provider.list_review_cases(status=status, priority=priority)
    return paginated_response(rows, request_id=request.state.request_id, limit=limit, offset=offset)


@router.get("/review-cases/{review_case_id}")
def get_review_case(review_case_id: str, request: Request) -> dict[str, object]:
    return success_response(_require_review_case(review_case_id), request_id=request.state.request_id)


@router.get("/review-cases/{review_case_id}/corrections")
def get_corrections(review_case_id: str, request: Request, limit: int = Query(DEFAULT_PAGE_SIZE, ge=1, le=MAX_PAGE_SIZE), offset: int = Query(0, ge=0)) -> dict[str, object]:
    _require_review_case(review_case_id)
    return paginated_response(local_provider.list_corrections(review_case_id), request_id=request.state.request_id, limit=limit, offset=offset)


@router.get("/reprocess-plans")
def list_reprocess_plans(request: Request, limit: int = Query(DEFAULT_PAGE_SIZE, ge=1, le=MAX_PAGE_SIZE), offset: int = Query(0, ge=0)) -> dict[str, object]:
    return paginated_response(local_provider.list_reprocess_plans(), request_id=request.state.request_id, limit=limit, offset=offset)
