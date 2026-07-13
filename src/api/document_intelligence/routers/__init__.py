"""Routers for the Document Intelligence API."""

from .health import root_router, versioned_router

__all__ = ["root_router", "versioned_router"]

