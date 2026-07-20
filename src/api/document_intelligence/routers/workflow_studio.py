"""Guarded Workflow Management API; governance only, never runtime execution."""
from __future__ import annotations
from collections.abc import Mapping
from typing import Any
from fastapi import APIRouter, Body, Query, Request
from src.security import Permission
from ..auth import authorize_mutation, authorize_read
from ..contracts import PaginationMetadata, ResponseMetadata
from ..errors import DocumentIntelligenceAPIError
from ..providers.workflow_studio_provider import WorkflowStudioAPIProvider, WorkflowStudioProviderError
from ..responses import success_response

router = APIRouter(prefix="/api/v1")

def _provider(request: Request) -> WorkflowStudioAPIProvider:
    value = getattr(request.app.state, "document_intelligence_workflow_studio_provider", None)
    if not isinstance(value, WorkflowStudioAPIProvider):
        raise DocumentIntelligenceAPIError("provider_configuration_error", "Workflow Studio is unavailable.", status_code=500)
    return value

def _tenant(scope) -> str:
    return scope.tenant_id or "disabled-workflow-scope"

def _mutation(request: Request, permission: Permission, workflow_id: str | None = None):
    scope = authorize_mutation(request, permission, resource_type="workflow_definition", resource_id=workflow_id)
    if not scope.enabled or scope.tenant_id is None or scope.principal_id is None:
        raise DocumentIntelligenceAPIError("workflow_management_not_enabled", "Workflow management mutations require authenticated authorization.", status_code=503)
    return scope

def _call(operation):
    try:
        return operation()
    except WorkflowStudioProviderError as exc:
        raise DocumentIntelligenceAPIError(exc.code, exc.message, status_code=exc.status_code) from None
    except (TypeError, ValueError):
        raise DocumentIntelligenceAPIError("invalid_request", "Request body is invalid.") from None

def _page(rows, total, request, limit, offset):
    metadata = ResponseMetadata(pagination=PaginationMetadata(limit, offset, total))
    return success_response(rows, request_id=request.state.request_id, metadata=metadata)

@router.get("/workflow-definitions")
def list_workflow_definitions(request: Request, limit: int = Query(50, ge=1, le=100), offset: int = Query(0, ge=0, le=10_000)):
    scope = authorize_read(request, Permission.WORKFLOW_READ, resource_type="workflow_definition_collection")
    rows, total = _call(lambda: _provider(request).list_definitions(_tenant(scope), limit=limit, offset=offset))
    return _page(rows, total, request, limit, offset)

@router.get("/workflow-definitions/{workflow_id}")
def get_workflow_definition(workflow_id: str, request: Request):
    scope = authorize_read(request, Permission.WORKFLOW_READ, resource_type="workflow_definition", resource_id=workflow_id, conceal_unauthorized_resource=True)
    row = _call(lambda: _provider(request).get_definition(_tenant(scope), workflow_id))
    if row is None: raise DocumentIntelligenceAPIError("workflow_not_found", "Workflow resource was not found.", status_code=404)
    return success_response(row, request_id=request.state.request_id)

@router.get("/workflow-definitions/{workflow_id}/versions")
def list_workflow_versions(workflow_id: str, request: Request, limit: int = Query(50, ge=1, le=100), offset: int = Query(0, ge=0, le=10_000)):
    scope = authorize_read(request, Permission.WORKFLOW_READ, resource_type="workflow_version_collection", resource_id=workflow_id, conceal_unauthorized_resource=True)
    result = _call(lambda: _provider(request).list_versions(_tenant(scope), workflow_id, limit=limit, offset=offset))
    if result is None: raise DocumentIntelligenceAPIError("workflow_not_found", "Workflow resource was not found.", status_code=404)
    return _page(result[0], result[1], request, limit, offset)

@router.get("/workflow-definitions/{workflow_id}/versions/{version_id}")
def get_workflow_version(workflow_id: str, version_id: str, request: Request):
    scope = authorize_read(request, Permission.WORKFLOW_READ, resource_type="workflow_version", resource_id=version_id, conceal_unauthorized_resource=True)
    row = _call(lambda: _provider(request).get_version(_tenant(scope), workflow_id, version_id))
    if row is None: raise DocumentIntelligenceAPIError("workflow_not_found", "Workflow resource was not found.", status_code=404)
    return success_response(row, request_id=request.state.request_id)

@router.get("/workflow-definitions/{workflow_id}/audit")
def get_workflow_audit(workflow_id: str, request: Request, limit: int = Query(50, ge=1, le=100), offset: int = Query(0, ge=0, le=10_000)):
    scope = authorize_read(request, Permission.WORKFLOW_READ, resource_type="workflow_audit", resource_id=workflow_id, conceal_unauthorized_resource=True)
    result = _call(lambda: _provider(request).audit(_tenant(scope), workflow_id, limit=limit, offset=offset))
    if result is None: raise DocumentIntelligenceAPIError("workflow_not_found", "Workflow resource was not found.", status_code=404)
    return _page(result[0], result[1], request, limit, offset)

@router.get("/workflow-operations")
def list_workflow_operations(request: Request):
    authorize_read(request, Permission.WORKFLOW_READ, resource_type="workflow_operation_catalog")
    return success_response(_provider(request).operations(), request_id=request.state.request_id)

@router.post("/workflow-definitions", status_code=201)
def create_workflow_definition(request: Request, payload: Mapping[str, Any] = Body(...)):
    s = _mutation(request, Permission.WORKFLOW_CREATE)
    return success_response(_call(lambda: _provider(request).create_workflow(s.tenant_id, s.principal_id, payload, request.state.request_id)), request_id=request.state.request_id)

@router.post("/workflow-definitions/{workflow_id}/versions", status_code=201)
def create_workflow_version(workflow_id: str, request: Request, payload: Mapping[str, Any] = Body(...)):
    s = _mutation(request, Permission.WORKFLOW_EDIT, workflow_id)
    return success_response(_call(lambda: _provider(request).create_version(s.tenant_id, workflow_id, s.principal_id, payload, request.state.request_id)), request_id=request.state.request_id)

@router.patch("/workflow-definitions/{workflow_id}/versions/{version_id}")
def update_workflow_version(workflow_id: str, version_id: str, request: Request, payload: Mapping[str, Any] = Body(...)):
    s = _mutation(request, Permission.WORKFLOW_EDIT, workflow_id)
    return success_response(_call(lambda: _provider(request).replace_draft(s.tenant_id, workflow_id, version_id, s.principal_id, payload, request.state.request_id)), request_id=request.state.request_id)

@router.post("/workflow-definitions/{workflow_id}/versions/{version_id}/validate")
def validate_workflow_version(workflow_id: str, version_id: str, request: Request):
    s = _mutation(request, Permission.WORKFLOW_EDIT, workflow_id)
    return success_response(_call(lambda: _provider(request).validate(s.tenant_id, workflow_id, version_id, s.principal_id)), request_id=request.state.request_id)

@router.post("/workflow-definitions/{workflow_id}/versions/{version_id}/test")
def test_workflow_version(workflow_id: str, version_id: str, request: Request, payload: Mapping[str, Any] = Body(...)):
    s = _mutation(request, Permission.WORKFLOW_TEST, workflow_id)
    return success_response(_call(lambda: _provider(request).test(s.tenant_id, workflow_id, version_id, s.principal_id, payload, request.state.request_id)), request_id=request.state.request_id)

@router.post("/workflow-definitions/{workflow_id}/versions/{version_id}/submit")
def submit_workflow_version(workflow_id: str, version_id: str, request: Request):
    s = _mutation(request, Permission.WORKFLOW_EDIT, workflow_id)
    return success_response(_call(lambda: _provider(request).submit(s.tenant_id, workflow_id, version_id, s.principal_id, request.state.request_id)), request_id=request.state.request_id)

@router.post("/workflow-definitions/{workflow_id}/versions/{version_id}/approve")
def approve_workflow_version(workflow_id: str, version_id: str, request: Request, payload: Mapping[str, Any] = Body(...)):
    s = _mutation(request, Permission.WORKFLOW_APPROVE, workflow_id)
    return success_response(_call(lambda: _provider(request).approve(s.tenant_id, workflow_id, version_id, s.principal_id, payload)), request_id=request.state.request_id)

@router.post("/workflow-definitions/{workflow_id}/versions/{version_id}/publish")
def publish_workflow_version(workflow_id: str, version_id: str, request: Request, payload: Mapping[str, Any] = Body(...)):
    s = _mutation(request, Permission.WORKFLOW_PUBLISH, workflow_id)
    return success_response(_call(lambda: _provider(request).publish(s.tenant_id, workflow_id, version_id, s.principal_id, payload, request.state.request_id)), request_id=request.state.request_id)

@router.post("/workflow-definitions/{workflow_id}/deactivate")
def deactivate_workflow(workflow_id: str, request: Request, payload: Mapping[str, Any] = Body(...)):
    s = _mutation(request, Permission.WORKFLOW_DEACTIVATE, workflow_id)
    return success_response(_call(lambda: _provider(request).deactivate(s.tenant_id, workflow_id, s.principal_id, payload, request.state.request_id)), request_id=request.state.request_id)

@router.post("/workflow-definitions/{workflow_id}/archive")
def archive_workflow(workflow_id: str, request: Request, payload: Mapping[str, Any] = Body(...)):
    s = _mutation(request, Permission.WORKFLOW_ADMIN, workflow_id)
    return success_response(_call(lambda: _provider(request).archive(s.tenant_id, workflow_id, s.principal_id, payload)), request_id=request.state.request_id)
