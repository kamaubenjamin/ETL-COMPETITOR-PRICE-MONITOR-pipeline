"""EntityWorkflowAdapter — hooks EntityConcurrencyGuard into Workflow Runtime stages.

This adapter wraps workflow stage functions with concurrency guard protection
for entity write operations.
"""

from __future__ import annotations

from typing import Any, Callable, Optional

from src.entity_runtime.concurrency.config import EntityConcurrencyConfig, DEFAULT_CONCURRENCY_CONFIG
from src.entity_runtime.concurrency.guard import EntityConcurrencyGuard
from src.entity_runtime.store.idempotency import EntityIdempotencyRegistry
from src.entity_runtime.store.version_store import EntityVersionRecord


class EntityWorkflowAdapter:
    """Adapter that hooks EntityConcurrencyGuard into Workflow Runtime stages.

    Wraps stage execution with concurrency guard protection, including:
    - Lease acquisition before entity write
    - Idempotency key generation and checking
    - CAS write with conflict detection and retry
    - Lease release after write
    - Graceful degradation when store is unavailable
    """

    def __init__(
        self,
        guard: EntityConcurrencyGuard,
        idempotency_registry: EntityIdempotencyRegistry,
        config: Optional[EntityConcurrencyConfig] = None,
    ) -> None:
        self._guard = guard
        self._idempotency_registry = idempotency_registry
        self._config = config or DEFAULT_CONCURRENCY_CONFIG

    def generate_idempotency_key(
        self,
        entity_type: str,
        source_document_id: str,
        entity_natural_key: str,
        workflow_run_id: str,
        stage_name: str,
    ) -> str:
        """Generate a deterministic idempotency key for entity operations.

        Args:
            entity_type: Entity class name.
            source_document_id: Document Runtime ID.
            entity_natural_key: Entity identifying fields.
            workflow_run_id: ExecutionContext.pipeline_run_id.
            stage_name: Workflow stage name.

        Returns:
            A hex-encoded SHA-256 hash string.
        """
        return self._idempotency_registry.generate_key(
            entity_type=entity_type,
            source_document_id=source_document_id,
            entity_natural_key=entity_natural_key,
            workflow_run_id=workflow_run_id,
            stage_name=stage_name,
        )

    def wrap_entity_stage(
        self,
        stage_fn: Callable[..., Any],
        entity_version_key: str,
        entity_type: str,
        entity_id: str,
        stage_name: str,
    ) -> Callable[..., Any]:
        """Wrap a stage function with concurrency guard protection.

        Args:
            stage_fn: The stage function to wrap.
            entity_version_key: The entity key for the operation.
            entity_type: Entity type discriminator.
            entity_id: Natural key within the entity type.
            stage_name: The workflow stage name.

        Returns:
            Wrapped function that performs entity writes through the guard.
        """

        def wrapped(*args: Any, **kwargs: Any) -> EntityVersionRecord:
            pipeline_run_id = kwargs.get("pipeline_run_id", "")
            data = kwargs.get("data", {})

            return self._guard.write_entity(
                entity_version_key=entity_version_key,
                data=data,
                entity_type=entity_type,
                entity_id=entity_id,
                pipeline_run_id=pipeline_run_id,
                stage_name=stage_name,
            )

        return wrapped

    def create_entity_writer(
        self,
        default_config: Optional[EntityConcurrencyConfig] = None,
    ) -> Callable[..., EntityVersionRecord]:
        """Factory for entity write operations.

        Args:
            default_config: Optional default configuration override.

        Returns:
            A callable that writes entities through the concurrency guard.
        """
        config = default_config or self._config

        def write_entity(
            entity_version_key: str,
            data: dict[str, Any],
            entity_type: str,
            entity_id: str,
            pipeline_run_id: str,
            stage_name: str,
        ) -> EntityVersionRecord:
            return self._guard.write_entity(
                entity_version_key=entity_version_key,
                data=data,
                entity_type=entity_type,
                entity_id=entity_id,
                pipeline_run_id=pipeline_run_id,
                stage_name=stage_name,
            )

        return write_entity

    @property
    def guard(self) -> EntityConcurrencyGuard:
        """Return the underlying concurrency guard."""
        return self._guard