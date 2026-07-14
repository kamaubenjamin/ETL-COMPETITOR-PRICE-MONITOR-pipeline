"""FastAPI application factory for the Document Intelligence API foundation."""

from __future__ import annotations

from datetime import datetime, timezone

from fastapi import FastAPI, Request
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from starlette.exceptions import HTTPException as StarletteHTTPException

from .contracts import API_VERSION
from .auth import create_auth_composition, create_runtime_auth_composition
from .config import APIAuthConfig
from .errors import DocumentIntelligenceAPIError
from .middleware import request_context_middleware
from .responses import error_response
from .routers import domain_routers, root_router, versioned_router
from .providers import FacadeDocumentIntelligenceProvider, facade_provider
from src.security.providers import IdentityProvider
from src.platform_runtime import (
    RuntimeComposition,
    RuntimeConfig,
    RuntimeErrorCode,
    RuntimeValidationError,
    assert_runtime_config_valid,
    compose_runtime,
)


def create_document_intelligence_app(
    *,
    auth_config: APIAuthConfig | None = None,
    identity_provider: IdentityProvider | None = None,
    runtime_config: RuntimeConfig | None = None,
    runtime_composition: RuntimeComposition | None = None,
    snapshot_at: str | None = None,
) -> FastAPI:
    if runtime_config is not None and runtime_composition is not None:
        raise RuntimeValidationError(RuntimeErrorCode.INVALID_CONFIG, field="runtime_mode")
    if (runtime_config is not None or runtime_composition is not None) and (
        auth_config is not None or identity_provider is not None
    ):
        raise RuntimeValidationError(RuntimeErrorCode.INVALID_CONFIG, field="auth")

    composed = runtime_composition
    runtime_auth = None
    if runtime_config is not None:
        safe_config = assert_runtime_config_valid(runtime_config)
        assert safe_config.auth is not None
        runtime_auth = create_runtime_auth_composition(safe_config.auth)
        composed = compose_runtime(
            safe_config,
            snapshot_at=snapshot_at or datetime.now(timezone.utc).isoformat(),
        )
    elif composed is not None:
        if not isinstance(composed, RuntimeComposition):
            raise RuntimeValidationError(RuntimeErrorCode.INVALID_CONFIG, field="runtime_mode")
        safe_config = assert_runtime_config_valid(composed.runtime_config)
        assert safe_config.auth is not None
        runtime_auth = create_runtime_auth_composition(safe_config.auth)

    application = FastAPI(
        title="Document Intelligence API",
        version=API_VERSION,
        description="Read-only API foundation for Document Intelligence consumers.",
    )
    application.state.document_intelligence_auth = (
        runtime_auth or create_auth_composition(auth_config, identity_provider)
    )
    application.state.document_intelligence_provider = (
        FacadeDocumentIntelligenceProvider(composed.query_facade)
        if composed is not None
        else facade_provider
    )
    application.state.platform_runtime = composed
    application.state.platform_runtime_summary = (
        composed.to_safe_dict()
        if composed is not None
        else {"mode": "compatibility_default", "composed": False}
    )
    if composed is not None:
        application.router.add_event_handler("shutdown", composed.close)

    @application.middleware("http")
    async def request_context(request: Request, call_next):
        return await request_context_middleware(request, call_next)

    @application.exception_handler(DocumentIntelligenceAPIError)
    async def document_intelligence_error(request: Request, exc: DocumentIntelligenceAPIError):
        return JSONResponse(
            status_code=exc.status_code,
            content=error_response(
                code=exc.code,
                message=exc.message,
                details=exc.details,
                request_id=request.state.request_id,
            ),
        )

    @application.exception_handler(StarletteHTTPException)
    async def http_error(request: Request, exc: StarletteHTTPException):
        if exc.status_code == 404:
            code, message = "not_found", "Resource not found."
        elif exc.status_code == 405:
            code, message = "method_not_allowed", "Method is not allowed."
        else:
            code, message = "http_error", "Request could not be completed."
        return JSONResponse(
            status_code=exc.status_code,
            content=error_response(code=code, message=message, request_id=request.state.request_id),
        )

    @application.exception_handler(RequestValidationError)
    async def request_validation_error(request: Request, exc: RequestValidationError):
        return JSONResponse(
            status_code=400,
            content=error_response(
                code="invalid_request",
                message="Request parameters are invalid.",
                request_id=request.state.request_id,
            ),
        )

    application.include_router(root_router)
    application.include_router(versioned_router)
    for router in domain_routers:
        application.include_router(router)
    return application


app = create_document_intelligence_app()
