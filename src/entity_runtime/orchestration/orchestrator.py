"""EntityRuntimeOrchestrator — orchestrates Entity Runtime execution with concurrency support.

Integrated with EntityConcurrencyGuard to provide:
  - Versioned entity writes with compare-and-swap semantics
  - Optimistic locking with automatic conflict detection and retry
  - Pessimistic lock escalation for hot entities
  - Execution leases for crash recovery
  - Idempotency protection for duplicate write prevention
  - Graceful degradation when version store is unavailable
  - Configuration-driven enable/disable behavior

When concurrency is disabled (ENTITY_VERSION_STORE_ENABLED=False),
behavior is identical to v1 Entity Runtime (no versioning).
"""

from __future__ import annotations

import logging
import os
from dataclasses import replace
from typing import Any, Optional

from src.entity_runtime.concurrency.config import (
    DEFAULT_CONCURRENCY_CONFIG,
    EntityConcurrencyConfig,
)
from src.entity_runtime.concurrency.errors import (
    EntityConflictError,
    EntityCorruptionError,
    EntityDuplicateWriteError,
    EntityLeaseError,
    EntityLeaseLostError,
    EntityLockTimeoutError,
    EntityStoreUnavailableError,
)
from src.entity_runtime.concurrency.guard import EntityConcurrencyGuard
from src.entity_runtime.concurrency.leases import LeaseManager
from src.entity_runtime.concurrency.optimistic import OptimisticLockManager
from src.entity_runtime.concurrency.pessimistic import PessimisticLockManager
from src.entity_runtime.contracts.entity_set import EntitySet
from src.entity_runtime.store.idempotency import EntityIdempotencyRegistry
from src.entity_runtime.store.version_store import EntityVersionRecord, EntityVersionStore

logger = logging.getLogger(__name__)


class EntityRuntimeOrchestrator:
    """Orchestrates Entity Runtime execution with pluggable extraction engine
    and optional concurrency guard.

    The orchestrator coordinates the full entity lifecycle:
      1. Extract entities from pipeline result (via extraction engine)
      2. Optionally persist entities through EntityConcurrencyGuard
      3. Return EntitySet (backward compatible)

    When the concurrency guard is enabled, entities are written to the
    version store with optimistic locking. When disabled, entities are
    returned as in-memory EntitySet objects (original v1 behavior).
    """

    def __init__(
        self,
        extraction_engine: Any,
        concurrency_guard: Optional[EntityConcurrencyGuard] = None,
        config: Optional[EntityConcurrencyConfig] = None,
    ):
        self.extraction_engine = extraction_engine
        self._config = self._resolve_config(config)
        self._concurrency_guard = self._build_concurrency_guard(concurrency_guard)

    # ------------------------------------------------------------------
    # Properties
    # ------------------------------------------------------------------

    @property
    def concurrency_enabled(self) -> bool:
        """Whether the concurrency guard is active."""
        return (
            self._concurrency_guard is not None
            and self._config.entity_version_store_enabled
        )

    @property
    def concurrency_guard(self) -> Optional[EntityConcurrencyGuard]:
        """Return the underlying concurrency guard, if any."""
        return self._concurrency_guard

    # ------------------------------------------------------------------
    # Core run method
    # ------------------------------------------------------------------

    def run(
        self,
        pipeline_result: Any,
        pipeline_run_id: str = "",
        stage_name: str = "entity_extract",
    ) -> EntitySet:
        """Execute entity extraction and optionally persist through concurrency guard.

        Args:
            pipeline_result: Output from Document Runtime or previous stage.
            pipeline_run_id: The workflow run identifier for provenance.
            stage_name: The workflow stage name for idempotency key generation.

        Returns:
            An EntitySet with extracted entities.

        Raises:
            RuntimeError: If extraction fails catastrophically.
        """
        # 1. Extract entities using the extraction engine
        entity_set = self.extraction_engine.extract(pipeline_result)

        if not isinstance(entity_set, EntitySet):
            return entity_set

        if not self.concurrency_enabled:
            logger.debug(
                "Entity version store disabled; returning in-memory EntitySet for %s",
                entity_set.source_document_id,
            )
            return entity_set

        # 2. Persist entities through concurrency guard (if enabled)
        return self._persist_entity_set(entity_set, pipeline_run_id, stage_name)

    # ------------------------------------------------------------------
    # Entity persistence methods
    # ------------------------------------------------------------------

    def _persist_entity_set(
        self,
        entity_set: EntitySet,
        pipeline_run_id: str,
        stage_name: str,
    ) -> EntitySet:
        """Persist all entities in an EntitySet through the concurrency guard.

        Writes each entity type (suppliers, customers, line_items, references,
        financials) as versioned records in the entity version store.

        On failure, logs a warning and returns the original EntitySet
        (graceful degradation).
        """
        guard = self._concurrency_guard
        if guard is None:
            return entity_set

        source_doc_id = entity_set.source_document_id
        max_version = 0

        try:
            # Persist suppliers
            for supplier in entity_set.suppliers:
                entity_key = f"supplier:{source_doc_id}:{self._entity_natural_key(supplier)}"
                record = guard.write_entity(
                    entity_version_key=entity_key,
                    data=supplier.to_dict() if hasattr(supplier, 'to_dict') else self._entity_to_dict(supplier),
                    entity_type="supplier",
                    entity_id=getattr(supplier, "name", "") or getattr(supplier, "supplier_name", ""),
                    pipeline_run_id=pipeline_run_id,
                    stage_name=stage_name,
                )
                max_version = max(max_version, record.version)
                self._apply_persisted_version(supplier, record.version)

            # Persist customers
            for customer in entity_set.customers:
                entity_key = f"customer:{source_doc_id}:{self._entity_natural_key(customer)}"
                record = guard.write_entity(
                    entity_version_key=entity_key,
                    data=self._entity_to_dict(customer),
                    entity_type="customer",
                    entity_id=getattr(customer, "name", "") or getattr(customer, "customer_name", ""),
                    pipeline_run_id=pipeline_run_id,
                    stage_name=stage_name,
                )
                max_version = max(max_version, record.version)
                self._apply_persisted_version(customer, record.version)

            # Persist line items
            for line_item in entity_set.line_items:
                entity_key = f"line_item:{source_doc_id}:{self._entity_natural_key(line_item)}"
                record = guard.write_entity(
                    entity_version_key=entity_key,
                    data=self._entity_to_dict(line_item),
                    entity_type="line_item",
                    entity_id=getattr(line_item, "sku", "") or getattr(line_item, "product_name", ""),
                    pipeline_run_id=pipeline_run_id,
                    stage_name=stage_name,
                )
                max_version = max(max_version, record.version)
                self._apply_persisted_version(line_item, record.version)

            # Persist document references
            for ref in entity_set.references:
                entity_key = f"document_reference:{source_doc_id}:{self._entity_natural_key(ref)}"
                record = guard.write_entity(
                    entity_version_key=entity_key,
                    data=self._entity_to_dict(ref),
                    entity_type="document_reference",
                    entity_id=getattr(ref, "document_id", "") or getattr(ref, "reference_number", ""),
                    pipeline_run_id=pipeline_run_id,
                    stage_name=stage_name,
                )
                max_version = max(max_version, record.version)
                self._apply_persisted_version(ref, record.version)

            # Persist financials
            for financial in entity_set.financials:
                entity_key = f"document_financials:{source_doc_id}:{self._entity_natural_key(financial)}"
                record = guard.write_entity(
                    entity_version_key=entity_key,
                    data=self._entity_to_dict(financial),
                    entity_type="document_financials",
                    entity_id=source_doc_id,
                    pipeline_run_id=pipeline_run_id,
                    stage_name=stage_name,
                )
                max_version = max(max_version, record.version)
                self._apply_persisted_version(financial, record.version)

            # Update entity_set version to reflect persistence
            if max_version > 0:
                self._apply_persisted_version(entity_set, max_version)

        except EntityStoreUnavailableError:
            logger.warning(
                "Entity version store unavailable for %s; "
                "returning in-memory EntitySet (graceful degradation)",
                source_doc_id,
            )
        except EntityConflictError as e:
            logger.warning(
                "Entity conflict detected for %s (expected v%d, got v%d); "
                "returning in-memory EntitySet",
                source_doc_id,
                e.expected_version,
                e.actual_version,
            )
        except (EntityLeaseError, EntityLeaseLostError) as e:
            logger.warning(
                "Entity lease error for %s: %s; returning in-memory EntitySet",
                source_doc_id,
                e,
            )
        except (EntityCorruptionError, EntityDuplicateWriteError, EntityLockTimeoutError) as e:
            logger.warning(
                "Entity write error for %s: %s; returning in-memory EntitySet",
                source_doc_id,
                e,
            )
        except Exception as e:
            logger.error(
                "Unexpected error persisting entity set %s: %s; "
                "returning in-memory EntitySet",
                source_doc_id,
                e,
            )

        return entity_set

    # ------------------------------------------------------------------
    # Entity version read methods
    # ------------------------------------------------------------------

    def read_entity(self, entity_version_key: str) -> Optional[EntityVersionRecord]:
        """Read the current active version of an entity from the version store.

        Args:
            entity_version_key: Composite key for the entity.

        Returns:
            The active EntityVersionRecord, or None.
        """
        if not self.concurrency_enabled or self._concurrency_guard is None:
            return None
        return self._concurrency_guard.read_entity(entity_version_key)

    def read_entity_history(
        self, entity_version_key: str
    ) -> list[EntityVersionRecord]:
        """Read the full version history for an entity.

        Args:
            entity_version_key: Composite key for the entity.

        Returns:
            List of EntityVersionRecord ordered by version.
        """
        if not self.concurrency_enabled or self._concurrency_guard is None:
            return []
        return self._concurrency_guard.read_entity_history(entity_version_key)

    # ------------------------------------------------------------------
    # Lease management
    # ------------------------------------------------------------------

    def acquire_lease(
        self,
        entity_version_key: str,
        holder_id: str,
        lease_duration_s: int = 120,
    ) -> bool:
        """Acquire an execution lease for the given entity.

        Args:
            entity_version_key: The entity key to acquire the lease for.
            holder_id: Unique identifier for the lease holder.
            lease_duration_s: Lease TTL in seconds.

        Returns:
            True if the lease was acquired, False otherwise.
        """
        if not self.concurrency_enabled or self._concurrency_guard is None:
            return True  # No-op when concurrency disabled
        return self._concurrency_guard.acquire_lease(
            entity_version_key=entity_version_key,
            holder_id=holder_id,
            lease_duration_s=lease_duration_s,
        )

    def release_lease(
        self, entity_version_key: str, holder_id: str
    ) -> bool:
        """Release an execution lease.

        Args:
            entity_version_key: The entity key to release the lease for.
            holder_id: The current lease holder identifier.

        Returns:
            True if the lease was released, False otherwise.
        """
        if not self.concurrency_enabled or self._concurrency_guard is None:
            return True  # No-op when concurrency disabled
        return self._concurrency_guard.release_lease(
            entity_version_key=entity_version_key,
            holder_id=holder_id,
        )

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------

    def _build_concurrency_guard(
        self,
        concurrency_guard: Optional[EntityConcurrencyGuard],
    ) -> Optional[EntityConcurrencyGuard]:
        """Build a default concurrency guard when the feature is enabled."""
        if concurrency_guard is not None:
            return concurrency_guard
        if not self._config.entity_version_store_enabled:
            return None

        try:
            db_path = self._config.entity_version_store_db_path
            parent_dir = os.path.dirname(db_path)
            if parent_dir:
                os.makedirs(parent_dir, exist_ok=True)

            store = EntityVersionStore(db_path=db_path)
            store.initialize_schema()
            idempotency_registry = EntityIdempotencyRegistry(db_path=db_path)
            optimistic_manager = OptimisticLockManager(version_store=store, config=self._config)
            pessimistic_manager = PessimisticLockManager(config=self._config, db_path=db_path)
            lease_manager = LeaseManager(config=self._config, db_path=db_path)
            return EntityConcurrencyGuard(
                version_store=store,
                optimistic_manager=optimistic_manager,
                pessimistic_manager=pessimistic_manager,
                lease_manager=lease_manager,
                idempotency_registry=idempotency_registry,
                config=self._config,
            )
        except Exception as exc:  # pragma: no cover - defensive fallback
            logger.warning(
                "Unable to initialize entity concurrency guard; falling back to in-memory behavior: %s",
                exc,
            )
            return None

    @staticmethod
    def _resolve_config(config: Optional[EntityConcurrencyConfig]) -> EntityConcurrencyConfig:
        """Resolve configuration, allowing environment-based opt-in for Phase 3 integration."""
        if config is not None:
            return config

        enabled_value = os.getenv("ENTITY_VERSION_STORE_ENABLED", "").strip().lower()
        enabled = enabled_value in {"1", "true", "yes", "on"}
        db_path = os.getenv("ENTITY_VERSION_STORE_DB_PATH", "").strip()
        if not db_path:
            db_path = DEFAULT_CONCURRENCY_CONFIG.entity_version_store_db_path
        return replace(
            DEFAULT_CONCURRENCY_CONFIG,
            entity_version_store_enabled=enabled,
            entity_version_store_db_path=db_path,
        )

    @staticmethod
    def _apply_persisted_version(entity: Any, version: int) -> None:
        """Attach the persisted version to entity-like objects when available."""
        if version <= 0:
            return
        try:
            object.__setattr__(entity, "entity_version", version)
        except Exception:
            try:
                setattr(entity, "entity_version", version)
            except Exception:
                logger.debug("Unable to attach entity version to %s", type(entity).__name__)

    @staticmethod
    def _entity_natural_key(entity: Any) -> str:
        """Generate a deterministic natural key for an entity.

        Uses the entity's primary identifier field if available,
        or falls back to a hash of its dict representation.
        """
        if hasattr(entity, "natural_key"):
            key = entity.natural_key()
            if key:
                return str(key).lower().replace(" ", "-")

        # Try common identifier fields
        for attr in ("name", "supplier_name", "customer_name", "sku",
                     "product_name", "document_id", "reference_number",
                     "invoice_number", "id", "identifier"):
            val = getattr(entity, attr, None)
            if val:
                return str(val).lower().replace(" ", "-")

        # Fallback: use a hash of the entity dict
        import hashlib
        import json
        raw = json.dumps(
            EntityRuntimeOrchestrator._entity_to_dict(entity),
            sort_keys=True,
            default=str,
        )
        return hashlib.md5(raw.encode()).hexdigest()[:16]

    @staticmethod
    def _entity_to_dict(entity: Any) -> dict[str, Any]:
        """Convert an entity to a dictionary for version store persistence.

        Respects to_dict() if available, otherwise uses dataclass fields.
        """
        if hasattr(entity, "to_dict"):
            return entity.to_dict()
        if hasattr(entity, "__dataclass_fields__"):
            import dataclasses
            return dataclasses.asdict(entity)
        if isinstance(entity, dict):
            return entity
        return {"value": str(entity)}