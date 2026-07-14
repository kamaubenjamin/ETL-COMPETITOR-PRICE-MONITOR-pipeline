"""Guarded metadata-only upload contracts; staging remains unavailable."""

from typing import Any

from fastapi import APIRouter, Body, Query, Request

from src.security import Permission

from ..auth import authorize_mutation, authorize_read
from ..contracts import DEFAULT_PAGE_SIZE, MAX_PAGE_SIZE
from ..errors import DocumentIntelligenceAPIError
from ..providers.upload_provider import ReadOnlyUploadProvider
from ..responses import paginated_response, success_response


router = APIRouter(prefix="/api/v1")


def _provider(request: Request) -> ReadOnlyUploadProvider:
    configured = getattr(request.app.state, "document_intelligence_upload_provider", None)
    if not isinstance(configured, ReadOnlyUploadProvider):
        raise DocumentIntelligenceAPIError(
            "provider_configuration_error", "Upload information could not be read.", status_code=500
        )
    return configured


def _staging_not_enabled() -> None:
    raise DocumentIntelligenceAPIError(
        "upload_staging_not_enabled",
        "Upload staging is not enabled.",
        status_code=503,
        details={"activation": "deferred"},
    )


@router.post("/documents/upload")
def upload_document(request: Request, payload: dict[str, Any] = Body(...)) -> None:
    scope = authorize_mutation(request, Permission.DOCUMENT_INGEST, resource_type="document_upload")
    if not scope.enabled:
        _staging_not_enabled()
    try:
        _command, validation = _provider(request).validate_request(
            payload,
            tenant_id=scope.tenant_id,
            actor_id=scope.principal_id,
            request_id=request.state.request_id,
        )
    except (TypeError, ValueError):
        raise DocumentIntelligenceAPIError(
            "invalid_upload_metadata", "Upload metadata is invalid.", status_code=400
        ) from None
    if not validation.valid:
        first = validation.issues[0]
        raise DocumentIntelligenceAPIError(
            "upload_validation_failed",
            "Upload validation failed.",
            status_code=400,
            details={"issue_code": first.code, "field": first.field, "issue_count": len(validation.issues)},
        )
    _staging_not_enabled()


@router.get("/uploads")
def list_uploads(
    request: Request,
    limit: int = Query(DEFAULT_PAGE_SIZE, ge=1, le=MAX_PAGE_SIZE),
    offset: int = Query(0, ge=0),
) -> dict[str, object]:
    scope = authorize_read(request, Permission.DOCUMENT_LIST, resource_type="upload_collection")
    rows = _provider(request).list_uploads(tenant_id=scope.tenant_id)
    return paginated_response(rows, request_id=request.state.request_id, limit=limit, offset=offset)


@router.get("/uploads/{upload_id}")
def get_upload(upload_id: str, request: Request) -> dict[str, object]:
    scope = authorize_read(
        request,
        Permission.DOCUMENT_READ,
        resource_type="upload",
        resource_id=upload_id,
        conceal_unauthorized_resource=True,
    )
    row = _provider(request).get_upload(upload_id, tenant_id=scope.tenant_id)
    if row is None:
        raise DocumentIntelligenceAPIError("upload_not_found", "Upload was not found.", status_code=404)
    return success_response(row, request_id=request.state.request_id)
