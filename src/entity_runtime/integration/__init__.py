"""Entity Runtime Integration — Workflow Runtime adapter for entity concurrency hardening.

Hooks EntityConcurrencyGuard into Workflow Runtime stages for protected entity writes.
"""

from src.entity_runtime.integration.workflow_adapter import EntityWorkflowAdapter

__all__ = [
    "EntityWorkflowAdapter",
]