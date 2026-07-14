"""Disabled-by-default export API contracts and safe read projections."""

from fastapi import APIRouter, Query, Request

from src.security import Permission

from ..auth import authorize_read
from ..contracts import DEFAULT_PAGE_SIZE, MAX_PAGE_SIZE
from ..errors import DocumentIntelligenceAPIError
from ..providers.export_provider import ReadOnlyExportProvider
from ..responses import paginated_response, success_response


router = APIRouter(prefix="/api/v1")


def _provider(request: Request) -> ReadOnlyExportProvider:
    configured = getattr(request.app.state, "document_intelligence_export_provider", None)
    if not isinstance(configured, ReadOnlyExportProvider):
        raise DocumentIntelligenceAPIError(
            "provider_configuration_error", "Export history could not be read.", status_code=500
        )
    return configured


def _mutation_not_enabled() -> None:
    raise DocumentIntelligenceAPIError(
        "mutation_not_enabled",
        "Export execution is not enabled.",
        status_code=503,
        details={"activation": "deferred"},
    )


@router.get("/documents/{document_id}/exports")
def list_document_exports(
    document_id: str,
    request: Request,
    limit: int = Query(DEFAULT_PAGE_SIZE, ge=1, le=MAX_PAGE_SIZE),
    offset: int = Query(0, ge=0),
) -> dict[str, object]:
    scope = authorize_read(
        request,
        Permission.DOCUMENT_READ,
        resource_type="document_export_collection",
        resource_id=document_id,
        conceal_unauthorized_resource=True,
    )
    rows = _provider(request).list_attempts(tenant_id=scope.tenant_id, document_id=document_id)
    return paginated_response(rows, request_id=request.state.request_id, limit=limit, offset=offset)


@router.get("/export-attempts")
def list_export_attempts(
    request: Request,
    limit: int = Query(DEFAULT_PAGE_SIZE, ge=1, le=MAX_PAGE_SIZE),
    offset: int = Query(0, ge=0),
) -> dict[str, object]:
    scope = authorize_read(request, Permission.DOCUMENT_LIST, resource_type="export_attempt_collection")
    rows = _provider(request).list_attempts(tenant_id=scope.tenant_id)
    return paginated_response(rows, request_id=request.state.request_id, limit=limit, offset=offset)


@router.get("/export-attempts/{attempt_id}")
def get_export_attempt(attempt_id: str, request: Request) -> dict[str, object]:
    scope = authorize_read(
        request,
        Permission.DOCUMENT_READ,
        resource_type="export_attempt",
        resource_id=attempt_id,
        conceal_unauthorized_resource=True,
    )
    row = _provider(request).get_attempt(attempt_id, tenant_id=scope.tenant_id)
    if row is None:
        raise DocumentIntelligenceAPIError("export_attempt_not_found", "Export attempt was not found.", status_code=404)
    return success_response(row, request_id=request.state.request_id)


@router.post("/documents/{document_id}/export/prepare")
def prepare_document_export(document_id: str, request: Request) -> None:
    _mutation_not_enabled()


@router.post("/documents/{document_id}/export")
def export_document(document_id: str, request: Request) -> None:
    _mutation_not_enabled()
