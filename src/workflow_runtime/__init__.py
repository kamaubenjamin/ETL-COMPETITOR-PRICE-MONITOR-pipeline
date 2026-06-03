"""Workflow Runtime v1 — deterministic, sequential, immutable-artifact workflow execution.

This runtime sits above the document engine and orchestrates multi-stage
document processing pipelines. It does not parse documents itself.
"""

from src.workflow_runtime.dsl.workflow_parser import WorkflowParser
from src.workflow_runtime.dsl.workflow_validator import WorkflowValidator
from src.workflow_runtime.runtime.workflow_runner import WorkflowRunner
from src.workflow_runtime.workspace.workspace_registry import WorkspaceRegistry

# Locking sub-package exports (Phase 1 — Foundation)
from src.workflow_runtime.locking import (
    LockAcquisition,
    IdempotencyRecord,
    LockAcquisitionError,
    IdempotencyRejectionError,
    LockProviderError,
    LeaseRefreshError,
    LockProvider,
    LockProviderRegistry,
    WorkflowExecutionGuard,
    WorkflowIdempotencyRegistry,
)

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
