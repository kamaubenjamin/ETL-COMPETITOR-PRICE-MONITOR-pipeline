"""EntityWorkflowAdapter — hooks EntityConcurrencyGuard into Workflow Runtime stages.

This adapter wraps workflow stage functions with concurrency guard protection
for entity write operations, including error handling for all concurrency
error types and graceful degradation paths.

Typical usage in a workflow runner::

    guard = EntityConcurrencyGuard(...)
    adapter = EntityWorkflowAdapter(guard, idempotency_registry)

    # Wrap a stage that writes entities
    wrapped_fn = adapter.wrap_entity_stage(
        stage_fn=my_stage,
        entity_version_key="supplier:doc-1:acme-corp",
        entity_type="supplier",
        entity_id="acme-corp",
        stage_name="entity_extract",
    )
    result = wrapped_fn(pipeline_run_id="run-123", data={...})
"""

from __future__ import annotations

import logging
from typing import Any, Callable, Optional

from src.entity_runtime.concurrency.config import DEFAULT_CONCURRENCY_CONFIG, EntityConcurrencyConfig
from src.entity_runtime.concurrency.errors import (
    EntityConflictError,
    EntityCorruptionError,
    EntityDeadlockError,
    EntityDuplicateWriteError,
    EntityLeaseError,
    EntityLeaseLostError,
    EntityLockTimeoutError,
    EntityStoreUnavailableError,
)
from src.entity_runtime.concurrency.guard import EntityConcurrencyGuard
from src.entity_runtime.store.idempotency import EntityIdempotencyRegistry
from src.entity_runtime.store.version_store import EntityVersionRecord

logger = logging.getLogger(__name__)


class EntityWorkflowAdapter:
    """Adapter that hooks EntityConcurrencyGuard into Workflow Runtime stages.

    Wraps stage execution with concurrency guard protection, including:
    - Lease acquisition before entity write
    - Idempotency key generation and checking
    - CAS write with conflict detection and retry
    - Lease release after write
    - Graceful degradation when store is unavailable
    - Typed error handling for all concurrency error types
    """

    def __init__(
        self,
        guard: EntityConcurrencyGuard,
        idempotency_registry: Optional[EntityIdempotencyRegistry] = None,
        config: Optional[EntityConcurrencyConfig] = None,
    ) -> None:
        self._guard = guard
        self._idempotency_registry = idempotency_registry
        self._config = config or DEFAULT_CONCURRENCY_CONFIG

    # ------------------------------------------------------------------
    # Idempotency key generation
    # ------------------------------------------------------------------

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
            entity_type: Entity class name (supplier, customer, line_item, etc.).
            source_document_id: Document Runtime ID.
            entity_natural_key: Entity identifying fields.
            workflow_run_id: ExecutionContext.pipeline_run_id.
            stage_name: Workflow stage name.

        Returns:
            A hex-encoded SHA-256 hash string.
        """
        if self._idempotency_registry is not None:
            return self._idempotency_registry.generate_key(
                entity_type=entity_type,
                source_document_id=source_document_id,
                entity_natural_key=entity_natural_key,
                workflow_run_id=workflow_run_id,
                stage_name=stage_name,
            )
        # Fallback: generate a simple deterministic key without the registry
        import hashlib
        raw = f"{entity_type}:{source_document_id}:{entity_natural_key}:{workflow_run_id}:{stage_name}"
        return hashlib.sha256(raw.encode()).hexdigest()

    # ------------------------------------------------------------------
    # Stage wrapping
    # ------------------------------------------------------------------

    def wrap_entity_stage(
        self,
        stage_fn: Callable[..., Any],
        entity_version_key: str,
        entity_type: str,
        entity_id: str,
        stage_name: str,
    ) -> Callable[..., Any]:
        """Wrap a stage function with concurrency guard protection.

        The wrapped function will:
        1. Call the original stage function
        2. Write entities through the concurrency guard
        3. Handle concurrency errors with appropriate fallback

        Args:
            stage_fn: The stage function to wrap.
            entity_version_key: The entity key for the operation.
            entity_type: Entity type discriminator.
            entity_id: Natural key within the entity type.
            stage_name: The workflow stage name for idempotency.

        Returns:
            Wrapped function that performs entity writes through the guard.
        """

        def wrapped(*args: Any, **kwargs: Any) -> Any:
            pipeline_run_id = kwargs.get("pipeline_run_id", "")
            data = kwargs.get("data", {})

            # First call the original stage function
            stage_result = stage_fn(*args, **kwargs)

            try:
                # Then write through concurrency guard
                return self._guard.write_entity(
                    entity_version_key=entity_version_key,
                    data=data or (stage_result if isinstance(stage_result, dict) else {}),
                    entity_type=entity_type,
                    entity_id=entity_id,
                    pipeline_run_id=pipeline_run_id,
                    stage_name=stage_name,
                )
            except EntityStoreUnavailableError:
                logger.warning(
                    "Entity version store unavailable for %s; "
                    "returning stage result without persistence (graceful degradation)",
                    entity_version_key,
                )
                return stage_result
            except EntityConflictError as e:
                logger.warning(
                    "Entity conflict for %s (expected v%d, got v%d); "
                    "returning stage result without persistence",
                    entity_version_key,
                    e.expected_version,
                    e.actual_version,
                )
                return stage_result
            except (EntityLeaseError, EntityLeaseLostError) as e:
                logger.warning(
                    "Entity lease error for %s: %s; "
                    "returning stage result without persistence",
                    entity_version_key,
                    e,
                )
                return stage_result
            except (EntityCorruptionError, EntityDuplicateWriteError,
                    EntityLockTimeoutError, EntityDeadlockError) as e:
                logger.warning(
                    "Entity write error for %s: %s; "
                    "returning stage result without persistence",
                    entity_version_key,
                    e,
                )
                return stage_result

        return wrapped

    # ------------------------------------------------------------------
    # Entity writer factory
    # ------------------------------------------------------------------

    def create_entity_writer(
        self,
        default_config: Optional[EntityConcurrencyConfig] = None,
    ) -> Callable[..., EntityVersionRecord]:
        """Factory for entity write operations.

        Args:
            default_config: Optional default configuration override.

        Returns:
            A callable that writes entities through the concurrency guard,
            with full error handling and graceful degradation.
        """
        config = default_config or self._config

        def write_entity(
            entity_version_key: str,
            data: dict[str, Any],
            entity_type: str,
            entity_id: str,
            pipeline_run_id: str,
            stage_name: str,
        ) -> Optional[EntityVersionRecord]:
            try:
                return self._guard.write_entity(
                    entity_version_key=entity_version_key,
                    data=data,
                    entity_type=entity_type,
                    entity_id=entity_id,
                    pipeline_run_id=pipeline_run_id,
                    stage_name=stage_name,
                )
            except EntityStoreUnavailableError:
                logger.warning(
                    "Entity version store unavailable for %s (writer factory); "
                    "returning None (graceful degradation)",
                    entity_version_key,
                )
                return None
            except (EntityConflictError, EntityLeaseError, EntityLeaseLostError,
                    EntityCorruptionError, EntityDuplicateWriteError,
                    EntityLockTimeoutError, EntityDeadlockError) as e:
                logger.warning(
                    "Entity write error for %s: %s; "
                    "returning None (graceful degradation)",
                    entity_version_key,
                    e,
                )
                return None

        return write_entity

    # ------------------------------------------------------------------
    # Error handling utilities
    # ------------------------------------------------------------------

    @staticmethod
    def handle_concurrency_error(
        error: Exception,
        entity_version_key: str,
        fallback_result: Any = None,
    ) -> Any:
        """Handle a concurrency error with appropriate logging.

        Args:
            error: The exception to handle.
            entity_version_key: The entity key that experienced the error.
            fallback_result: Value to return on non-fatal errors.

        Returns:
            The fallback_result for recoverable errors, or re-raises for
            unrecoverable errors.
        """
        if isinstance(error, EntityStoreUnavailableError):
            logger.warning(
                "Store unavailable for %s; using fallback (graceful degradation)",
                entity_version_key,
            )
            return fallback_result
        if isinstance(error, (EntityConflictError, EntityLeaseError, EntityLeaseLostError)):
            logger.warning(
                "Recoverable concurrency error for %s: %s; using fallback",
                entity_version_key,
                error,
            )
            return fallback_result
        if isinstance(error, (EntityCorruptionError, EntityDuplicateWriteError,
                              EntityLockTimeoutError, EntityDeadlockError)):
            logger.warning(
                "Non-fatal write error for %s: %s; using fallback",
                entity_version_key,
                error,
            )
            return fallback_result
        # Re-raise unexpected errors
        raise error

    # ------------------------------------------------------------------
    # Properties
    # ------------------------------------------------------------------

    @property
    def guard(self) -> EntityConcurrencyGuard:
        """Return the underlying concurrency guard."""
        return self._guard

    @property
    def idempotency_registry(self) -> Optional[EntityIdempotencyRegistry]:
        """Return the idempotency registry, if available."""
        return self._idempotency_registry