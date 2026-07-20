"""Routers for the Document Intelligence API."""

from .audit import router as audit_router
from .documents import router as documents_router
from .exports import router as exports_router
from .health import root_router, versioned_router
from .matching import router as matching_router
from .uploads import router as uploads_router
from .reviews import router as reviews_router
from .validation import router as validation_router
from .workflows import router as workflows_router
from .workflow_studio import router as workflow_studio_router
from .session import router as session_router

domain_routers = (
    documents_router,
    exports_router,
    uploads_router,
    validation_router,
    matching_router,
    reviews_router,
    workflows_router,
    workflow_studio_router,
    session_router,
    audit_router,
)

__all__ = ["domain_routers", "root_router", "versioned_router"]
