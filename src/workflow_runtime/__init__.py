"""Workflow Runtime v1 — deterministic, sequential, immutable-artifact workflow execution.

This runtime sits above the document engine and orchestrates multi-stage
document processing pipelines. It does not parse documents itself.
"""

from __future__ import annotations

from importlib import import_module
from typing import Any

__all__ = [
    "WorkflowParser",
    "WorkflowValidator",
    "WorkflowRunner",
    "WorkspaceRegistry",
    # Locking
    "LockAcquisition",
    "IdempotencyRecord",
    "LockAcquisitionError",
    "IdempotencyRejectionError",
    "LockProviderError",
    "LeaseRefreshError",
    "LockProvider",
    "LockProviderRegistry",
    "WorkflowExecutionGuard",
    "WorkflowIdempotencyRegistry",
]

_LAZY_EXPORTS = {
    "WorkflowParser": ("src.workflow_runtime.dsl.workflow_parser", "WorkflowParser"),
    "WorkflowValidator": ("src.workflow_runtime.dsl.workflow_validator", "WorkflowValidator"),
    "WorkflowRunner": ("src.workflow_runtime.runtime.workflow_runner", "WorkflowRunner"),
    "WorkspaceRegistry": ("src.workflow_runtime.workspace.workspace_registry", "WorkspaceRegistry"),
    "LockAcquisition": ("src.workflow_runtime.locking", "LockAcquisition"),
    "IdempotencyRecord": ("src.workflow_runtime.locking", "IdempotencyRecord"),
    "LockAcquisitionError": ("src.workflow_runtime.locking", "LockAcquisitionError"),
    "IdempotencyRejectionError": ("src.workflow_runtime.locking", "IdempotencyRejectionError"),
    "LockProviderError": ("src.workflow_runtime.locking", "LockProviderError"),
    "LeaseRefreshError": ("src.workflow_runtime.locking", "LeaseRefreshError"),
    "LockProvider": ("src.workflow_runtime.locking", "LockProvider"),
    "LockProviderRegistry": ("src.workflow_runtime.locking", "LockProviderRegistry"),
    "WorkflowExecutionGuard": ("src.workflow_runtime.locking", "WorkflowExecutionGuard"),
    "WorkflowIdempotencyRegistry": ("src.workflow_runtime.locking", "WorkflowIdempotencyRegistry"),
}


def __getattr__(name: str) -> Any:
    """Load public runtime implementations only when a caller requests them."""

    target = _LAZY_EXPORTS.get(name)
    if target is None:
        raise AttributeError(f"module {__name__!r} has no attribute {name!r}")
    module_name, attribute_name = target
    value = getattr(import_module(module_name), attribute_name)
    globals()[name] = value
    return value


def __dir__() -> list[str]:
    return sorted(set(globals()) | set(__all__))
