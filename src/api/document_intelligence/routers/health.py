"""Health and status routes for the read-only API foundation."""

from __future__ import annotations

from fastapi import APIRouter, Request

from ..contracts import API_VERSION
from ..responses import success_response
from ..auth import authorize_read
from src.security import Permission


SERVICE_NAME = "document-intelligence-api"
SERVICE_MODE = "read_only_foundation"
CAPABILITIES = (
    "health",
    "pagination_metadata",
    "response_envelopes",
    "status",
)

root_router = APIRouter()
versioned_router = APIRouter(prefix="/api/v1")


def _request_id(request: Request) -> str:
    return request.state.request_id


def _health_data() -> dict[str, str]:
    return {"service": SERVICE_NAME, "status": "ok", "mode": SERVICE_MODE}


def _status_data() -> dict[str, object]:
    return {
        "service_name": SERVICE_NAME,
        "api_version": API_VERSION,
        "mode": SERVICE_MODE,
        "capabilities": list(CAPABILITIES),
    }


@root_router.get("/health")
def root_health(request: Request) -> dict[str, object]:
    return success_response(_health_data(), request_id=_request_id(request))


@versioned_router.get("/health")
def versioned_health(request: Request) -> dict[str, object]:
    return success_response(_health_data(), request_id=_request_id(request))


@versioned_router.get("/status")
def versioned_status(request: Request) -> dict[str, object]:
    authorize_read(request, Permission.DOCUMENT_LIST, resource_type="service_status")
    return success_response(_status_data(), request_id=_request_id(request))

