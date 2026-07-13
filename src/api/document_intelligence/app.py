"""FastAPI application factory for the Document Intelligence API foundation."""

from __future__ import annotations

from uuid import uuid4

from fastapi import FastAPI, Request
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from starlette.exceptions import HTTPException as StarletteHTTPException

from .contracts import API_VERSION
from .errors import DocumentIntelligenceAPIError
from .responses import error_response
from .routers import domain_routers, root_router, versioned_router


def _request_id(request: Request) -> str:
    supplied = request.headers.get("x-request-id", "")
    if supplied and len(supplied) <= 128 and supplied.isascii() and supplied.isprintable():
        return supplied
    return str(uuid4())


def create_document_intelligence_app() -> FastAPI:
    application = FastAPI(
        title="Document Intelligence API",
        version=API_VERSION,
        description="Read-only API foundation for Document Intelligence consumers.",
    )

    @application.middleware("http")
    async def request_context(request: Request, call_next):
        request.state.request_id = _request_id(request)
        response = await call_next(request)
        response.headers["x-request-id"] = request.state.request_id
        return response

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
        code = "not_found" if exc.status_code == 404 else "http_error"
        message = "Resource not found." if exc.status_code == 404 else "Request could not be completed."
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
