"""EntityConcurrencyGuard — orchestrator coordinating all concurrency components.

The guard integrates version store, optimistic/pessimistic locking, lease management,
and idempotency into a single protected write lifecycle.

Typical write lifecycle:
  1. Determine locking strategy (optimistic or pessimistic)
  2. Acquire execution lease
  3. Check idempotency
  4. Perform CAS write (with retry / escalation)
  5. Release lease
  6. Log conflicts if any
"""

from __future__ import annotations

import hashlib
import json
import logging
import os
import socket
import threading
from datetime import datetime, timezone
from typing import Any, Optional

from src.entity_runtime.concurrency.config import EntityConcurrencyConfig
from src.entity_runtime.concurrency.errors import (
    EntityConflictError,
    EntityCorruptionError,
    EntityDuplicateWriteError,
    EntityLeaseError,
    EntityLeaseLostError,
    EntityLockTimeoutError,
    EntityStoreUnavailableError,
)
from src.entity_runtime.concurrency.leases import LeaseAcquisition, LeaseManager
from src.entity_runtime.concurrency.optimistic import ConflictInfo, OptimisticLockManager
from src.entity_runtime.concurrency.pessimistic import PessimisticLockManager
from src.entity_runtime.store.idempotency import EntityIdempotencyRegistry, IdempotencyResult
from src.entity_runtime.store.version_store import EntityVersionRecord, EntityVersionStore

logger = logging.getLogger(__name__)


class EntityConcurrencyGuard:
    """Orchestrator for entity concurrency hardening.

    Coordinates the full entity write lifecycle including acquisition of
    execution leases, idempotency checking, compare-and-swap writes with
    optimistic or pessimistic locking, conflict logging, and lease release.
    """

    def __init__(
        self,
        version_store: EntityVersionStore,
        optimistic_manager: OptimisticLockManager,
        pessimistic_manager: PessimisticLockManager,
        lease_manager: LeaseManager,
        idempotency_registry: EntityIdempotencyRegistry,
        config: EntityConcurrencyConfig,
    ) -> None:
        self._version_store = version_store
        self._optimistic_manager = optimistic_manager
        self._pessimistic_manager = pessimistic_manager
        self._lease_manager = lease_manager
        self._idempotency_registry = idempotency_registry
        self._config = config
        self._hostname = socket.gethostname()

    @property
    def config(self) -> EntityConcurrencyConfig:
        return self._config

    @property
    def version_store(self) -> EntityVersionStore:
        return self._version_store

    # ------------------------------------------------------------------
    # Public API — write entity
    # ------------------------------------------------------------------

    def write_entity(
        self,
        entity_version_key: str,
        data: dict[str, Any],
        entity_type: str,
        entity_id: str,
        pipeline_run_id: str,
        stage_name: str,
    ) -> EntityVersionRecord:
        """Perform a fully protected entity write.

        Complete lifecycle: determine strategy -> acquire lease -> check
        idempotency -> CAS write -> release lease -> log conflicts.

        Args:
            entity_version_key: Composite key for the entity.
            data: Full entity data to write.
            entity_type: Entity type discriminator.
            entity_id: Natural key within the entity type.
            pipeline_run_id: The run performing this write.
            stage_name: The workflow stage name.

        Returns:
            The newly created EntityVersionRecord.

        Raises:
            EntityConflictError: If all retry attempts are exhausted.
            EntityLeaseError: If lease cannot be acquired.
            EntityStoreUnavailableError: If version store is unavailable.
        """
        if not self._config.entity_version_store_enabled:
            # Fallback: write through store directly without concurrency controls
            return self._write_without_guard(
                entity_version_key=entity_version_key,
                data=data,
                entity_type=entity_type,
                entity_id=entity_id,
                pipeline_run_id=pipeline_run_id,
            )

        holder_id = self._generate_holder_id(pipeline_run_id)
        lease: Optional[LeaseAcquisition] = None

        try:
            # 1. Acquire execution lease
            lease = self._lease_manager.acquire(
                entity_version_key=entity_version_key,
                holder_id=holder_id,
                lease_duration_s=self._config.entity_lease_default_s,
            )

            # 2. Start refresh loop
            self._lease_manager.start_refresh_loop(
                entity_version_key=entity_version_key,
                holder_id=holder_id,
                interval_s=self._config.entity_lease_refresh_interval_s,
                lease_duration_s=self._config.entity_lease_default_s,
            )

            # 3. Determine locking strategy
            if self._pessimistic_manager.should_escalate(entity_version_key):
                record = self._write_with_pessimistic(
                    entity_version_key=entity_version_key,
                    data=data,
                    entity_type=entity_type,
                    entity_id=entity_id,
                    pipeline_run_id=pipeline_run_id,
                )
            else:
                record = self._write_optimistic_with_idempotency(
                    entity_version_key=entity_version_key,
                    data=data,
                    entity_type=entity_type,
                    entity_id=entity_id,
                    pipeline_run_id=pipeline_run_id,
                    stage_name=stage_name,
                    holder_id=holder_id,
                )

            return record

        except EntityStoreUnavailableError:
            logger.warning(
                "Version store unavailable for %s, falling back to in-memory write",
                entity_version_key,
            )
            return self._write_without_guard(
                entity_version_key=entity_version_key,
                data=data,
                entity_type=entity_type,
                entity_id=entity_id,
                pipeline_run_id=pipeline_run_id,
            )

        except (EntityLeaseError, EntityLeaseLostError) as e:
            logger.error("Lease error for %s: %s", entity_version_key, e)
            raise

        finally:
            # Release lease
            if lease is not None:
                self._lease_manager.stop_refresh_loop(entity_version_key)
                self._lease_manager.release(
                    entity_version_key=entity_version_key,
                    holder_id=holder_id,
                )

    # ------------------------------------------------------------------
    # Public API — read operations
    # ------------------------------------------------------------------

    def read_entity(
        self, entity_version_key: str
    ) -> Optional[EntityVersionRecord]:
        """Read the current active version of an entity.

        Args:
            entity_version_key: Composite key for the entity.

        Returns:
            The active EntityVersionRecord, or None if the entity doesn't exist.
        """
        if not self._config.entity_version_store_enabled:
            return None
        try:
            return self._version_store.read_active(entity_version_key)
        except Exception as e:
            logger.warning("Failed to read entity %s: %s", entity_version_key, e)
            return None

    def read_entity_history(
        self, entity_version_key: str
    ) -> list[EntityVersionRecord]:
        """Read the full version history for an entity.

        Args:
            entity_version_key: Composite key for the entity.

        Returns:
            List of EntityVersionRecord ordered by version (v1, v2, ...).
        """
        if not self._config.entity_version_store_enabled:
            return []
        try:
            return self._version_store.read_history(entity_version_key)
        except Exception as e:
            logger.warning("Failed to read history for %s: %s", entity_version_key, e)
            return []

    # ------------------------------------------------------------------
    # Public API — merge entity
    # ------------------------------------------------------------------

    def merge_entity(
        self,
        entity_version_key: str,
        new_data: dict[str, Any],
        entity_type: str,
        entity_id: str,
        pipeline_run_id: str,
        stage_name: str,
    ) -> EntityVersionRecord:
        """Merge new data into an existing entity with CAS protection.

        Reads the current active version, merges the new data into it,
        then performs a CAS write. If the entity doesn't exist, creates
        version 1 with the new data.

        Args:
            entity_version_key: Composite key for the entity.
            new_data: New data to merge into the existing entity.
            entity_type: Entity type discriminator.
            entity_id: Natural key within the entity type.
            pipeline_run_id: The run performing this merge.
            stage_name: The workflow stage name.

        Returns:
            The new EntityVersionRecord after the merge.
        """
        # Read current active version
        active = self.read_entity(entity_version_key)

        if active is None:
            # Entity doesn't exist — write version 1 with merge data
            return self.write_entity(
                entity_version_key=entity_version_key,
                data=new_data,
                entity_type=entity_type,
                entity_id=entity_id,
                pipeline_run_id=pipeline_run_id,
                stage_name=stage_name,
            )

        # Merge new data into existing data
        merged_data = dict(active.data)
        merged_data.update(new_data)

        # Write merged data as new version
        return self.write_entity(
            entity_version_key=entity_version_key,
            data=merged_data,
            entity_type=entity_type,
            entity_id=entity_id,
            pipeline_run_id=pipeline_run_id,
            stage_name=stage_name,
        )

    # ------------------------------------------------------------------
    # Public API — conflict diagnostics
    # ------------------------------------------------------------------

    def get_conflict_info(
        self, entity_version_key: str
    ) -> Optional[ConflictInfo]:
        """Get conflict diagnostics for an entity.

        Args:
            entity_version_key: Composite key for the entity.

        Returns:
            ConflictInfo if there's an active conflict, None otherwise.
        """
        if not self._config.entity_version_store_enabled:
            return None
        try:
            active = self._version_store.read_active(entity_version_key)
            if active is None:
                return None
            return ConflictInfo(
                conflict_type="version_mismatch",
                expected_version=active.version,
                actual_version=active.version,
                expected_checksum=active.checksum,
                actual_checksum=active.checksum,
                current_holder=active.created_by,
                last_updated_at=active.created_at,
            )
        except Exception as e:
            logger.warning("Failed to get conflict info for %s: %s", entity_version_key, e)
            return None

    # ------------------------------------------------------------------
    # Public API — lease management
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
            True if the lease was acquired, False if held by another.
        """
        try:
            self._lease_manager.acquire(
                entity_version_key=entity_version_key,
                holder_id=holder_id,
                lease_duration_s=lease_duration_s,
            )
            return True
        except EntityLeaseError:
            return False

    def release_lease(
        self, entity_version_key: str, holder_id: str
    ) -> bool:
        """Release an execution lease.

        Args:
            entity_version_key: The entity key to release the lease for.
            holder_id: The current lease holder identifier.

        Returns:
            True if the lease was released, False if not held by holder_id.
        """
        return self._lease_manager.release(
            entity_version_key=entity_version_key,
            holder_id=holder_id,
        )

    # ------------------------------------------------------------------
    # Internal — write paths
    # ------------------------------------------------------------------

    def _write_optimistic_with_idempotency(
        self,
        entity_version_key: str,
        data: dict[str, Any],
        entity_type: str,
        entity_id: str,
        pipeline_run_id: str,
        stage_name: str,
        holder_id: str,
    ) -> EntityVersionRecord:
        """Write with optimistic locking and idempotency check.

        Generates an idempotency key from the operation parameters.
        If a duplicate is detected, returns the existing version.
        """
        # Generate idempotency key
        source_document_id = entity_version_key.split(":")[1] if ":" in entity_version_key else ""
        idempotency_key = self._idempotency_registry.generate_key(
            entity_type=entity_type,
            source_document_id=source_document_id,
            entity_natural_key=entity_id,
            workflow_run_id=pipeline_run_id,
            stage_name=stage_name,
        )

        # Check idempotency
        result = self._idempotency_registry.check_and_record(
            idempotency_key=idempotency_key,
            entity_version_key=entity_version_key,
            new_version=0,  # Will be updated after write
            pipeline_run_id=pipeline_run_id,
        )

        if result.status == "duplicate":
            # Return the existing version if duplicate
            active = self._version_store.read_active(entity_version_key)
            if active is not None:
                return active
            raise EntityDuplicateWriteError(
                idempotency_key=idempotency_key,
                entity_version_key=entity_version_key,
                existing_version=result.existing_version or 0,
                existing_run=result.existing_run or "",
            )

        # Read current version for CAS
        active = self._version_store.read_active(entity_version_key)
        expected_version = active.version if active is not None else 0
        expected_checksum = active.checksum if active is not None else ""

        try:
            # Perform CAS write with retry
            record = self._optimistic_manager.cas_write(
                entity_version_key=entity_version_key,
                data=data,
                expected_version=expected_version,
                expected_checksum=expected_checksum,
                entity_type=entity_type,
                entity_id=entity_id,
                created_by=pipeline_run_id,
                source_document_id=source_document_id,
            )

            # Record write attempt for conflict rate tracking
            self._pessimistic_manager.record_write_attempt(entity_version_key)

            # Mark idempotency as completed
            self._idempotency_registry.mark_completed(idempotency_key)

            return record

        except EntityConflictError as e:
            # Record conflict for escalation tracking
            self._pessimistic_manager.record_conflict(entity_version_key)
            self._pessimistic_manager.record_write_attempt(entity_version_key)

            # Log conflict
            active_now = self._version_store.read_active(entity_version_key)
            self._version_store.log_conflict(
                entity_version_key=entity_version_key,
                conflict_type="version_mismatch",
                attempted_version=expected_version,
                current_version=active_now.version if active_now else 0,
                attempted_by=pipeline_run_id,
                current_holder=active_now.created_by if active_now else "",
                resolution="retry",
            )

            raise

    def _write_with_pessimistic(
        self,
        entity_version_key: str,
        data: dict[str, Any],
        entity_type: str,
        entity_id: str,
        pipeline_run_id: str,
    ) -> EntityVersionRecord:
        """Write with pessimistic locking.

        Acquires an exclusive lock, reads the current version, and writes
        the new version with CAS semantics.
        """
        try:
            # Acquire pessimistic lock
            acquired = self._pessimistic_manager.acquire_locks(
                [entity_version_key],
                timeout_s=self._config.pessimistic_lock_acquire_timeout_s,
            )

            if not acquired:
                raise EntityLockTimeoutError(
                    entity_version_key=entity_version_key,
                    timeout_s=self._config.pessimistic_lock_acquire_timeout_s,
                )

            try:
                # Read current version
                active = self._version_store.read_active(entity_version_key)
                expected_version = active.version if active is not None else 0

                # Compute checksum
                checksum = EntityVersionStore.compute_checksum(data)
                source_document_id = (
                    entity_version_key.split(":")[1] if ":" in entity_version_key else ""
                )

                # Write via version store
                record = self._version_store.write_version(
                    entity_version_key=entity_version_key,
                    data=data,
                    expected_version=expected_version,
                    checksum=checksum,
                    entity_type=entity_type,
                    entity_id=entity_id,
                    created_by=pipeline_run_id,
                    source_document_id=source_document_id,
                )
                return record

            finally:
                # Release pessimistic locks
                self._pessimistic_manager.release_locks([entity_version_key])

        except EntityLockTimeoutError:
            logger.warning(
                "Pessimistic lock timeout for %s after %ds",
                entity_version_key,
                self._config.pessimistic_lock_acquire_timeout_s,
            )
            raise

    def _write_without_guard(
        self,
        entity_version_key: str,
        data: dict[str, Any],
        entity_type: str,
        entity_id: str,
        pipeline_run_id: str,
    ) -> EntityVersionRecord:
        """Write without concurrency guard (fallback or disabled mode).

        Writes through the version store with expected_version=0 (optimistic).
        If the store is unavailable, raises EntityStoreUnavailableError.
        """
        checksum = EntityVersionStore.compute_checksum(data)
        return self._version_store.write_version(
            entity_version_key=entity_version_key,
            data=data,
            expected_version=0,
            checksum=checksum,
            entity_type=entity_type,
            entity_id=entity_id,
            created_by=pipeline_run_id,
            source_document_id="",
        )

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------

    def _generate_holder_id(self, pipeline_run_id: str) -> str:
        """Generate a unique lease holder identifier.

        Format: '{hostname}-{pid}-{pipeline_run_id}'
        """
        return f"{self._hostname}-{os.getpid()}-{pipeline_run_id}"