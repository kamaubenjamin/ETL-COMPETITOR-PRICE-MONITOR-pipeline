"""OptimisticLockManager — compare-and-swap (CAS) write with conflict detection and retry.

Primary concurrency mechanism for entity writes. Uses CAS pattern:
  read_version -> compute_new -> cas_write(expected_version) -> conflict_check

When a conflict is detected, retries with exponential backoff with jitter.
"""

from __future__ import annotations

import random
import time
from dataclasses import dataclass
from typing import Any, Optional

from src.entity_runtime.concurrency.config import EntityConcurrencyConfig
from src.entity_runtime.concurrency.errors import EntityConflictError, EntityCorruptionError
from src.entity_runtime.store.version_store import EntityVersionRecord, EntityVersionStore


@dataclass(frozen=True, slots=True)
class ConflictInfo:
    """Details about a CAS conflict detected during an optimistic write.

    Attributes:
        conflict_type: 'version_mismatch' | 'checksum_mismatch' | 'entity_not_found'.
        expected_version: The version the writer expected.
        actual_version: The current version in the store.
        expected_checksum: The checksum the writer expected.
        actual_checksum: The checksum of the current version.
        current_holder: pipeline_run_id holding the latest version.
        last_updated_at: ISO timestamp of the last update.
    """

    conflict_type: str
    """'version_mismatch' | 'checksum_mismatch' | 'entity_not_found'."""

    expected_version: int
    """The version the writer expected."""

    actual_version: int
    """The current version in the store."""

    expected_checksum: str
    """The checksum the writer expected."""

    actual_checksum: str
    """The checksum of the current version in the store."""

    current_holder: str
    """pipeline_run_id holding the latest version."""

    last_updated_at: str
    """ISO-8601 timestamp of the last entity update."""


class OptimisticLockManager:
    """Concrete implementation of optimistic locking with CAS semantics.

    Manages the compare-and-swap write pattern including conflict detection,
    exponential backoff retry with jitter, and conflict diagnostics.

    Delegates to EntityVersionStore for the actual versioned CRUD operations.
    """

    def __init__(
        self,
        version_store: EntityVersionStore,
        config: EntityConcurrencyConfig,
    ) -> None:
        self._version_store = version_store
        self._config = config

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def cas_write(
        self,
        entity_version_key: str,
        data: dict[str, Any],
        expected_version: int,
        expected_checksum: str,
        entity_type: str,
        entity_id: str,
        created_by: str,
        source_document_id: str,
    ) -> EntityVersionRecord:
        """Perform a compare-and-swap write with automatic retry.

        Writes the new version only if the expected version matches the
        current active version. Retries on conflict with exponential backoff.

        Args:
            entity_version_key: Composite key for the entity.
            data: Full entity data to write.
            expected_version: The version the writer expects to replace.
            expected_checksum: The checksum of the expected version's data.
            entity_type: Entity type discriminator.
            entity_id: Natural key within the entity type.
            created_by: pipeline_run_id that created this version.
            source_document_id: Document that produced this version.

        Returns:
            The newly created EntityVersionRecord.

        Raises:
            EntityConflictError: If all retry attempts are exhausted.
            EntityCorruptionError: If a checksum mismatch is detected.
        """
        max_attempts = self._config.optimistic_retry_max_attempts
        base_delay_ms = self._config.optimistic_retry_base_delay_ms
        max_delay_ms = self._config.optimistic_retry_max_delay_ms
        multiplier = self._config.optimistic_retry_backoff_multiplier

        last_exception: Optional[Exception] = None

        for attempt in range(max_attempts):
            try:
                record = self._version_store.write_version(
                    entity_version_key=entity_version_key,
                    data=data,
                    expected_version=expected_version,
                    checksum=expected_checksum,
                    entity_type=entity_type,
                    entity_id=entity_id,
                    created_by=created_by,
                    source_document_id=source_document_id,
                )
                return record
            except EntityConflictError as e:
                last_exception = e
                if attempt >= max_attempts - 1:
                    # Last attempt failed — raise
                    raise

                # Re-read the current version for retry
                active = self._version_store.read_active(entity_version_key)
                if active is not None:
                    expected_version = active.version
                    expected_checksum = active.checksum
                else:
                    expected_version = 0
                    expected_checksum = ""

                # Exponential backoff with jitter
                delay = self._compute_retry_delay(attempt, base_delay_ms, max_delay_ms, multiplier)
                time.sleep(delay)

            except EntityCorruptionError:
                # Corruption is not retryable — raise immediately
                raise

        # Should not reach here, but guard against edge cases
        if last_exception is not None:
            raise last_exception
        raise EntityConflictError(
            entity_version_key=entity_version_key,
            expected_version=expected_version,
            actual_version=-1,
            message="CAS write failed after all retry attempts",
        )

    def detect_conflict(
        self,
        entity_version_key: str,
        expected_version: int,
        expected_checksum: str,
    ) -> Optional[ConflictInfo]:
        """Detect if a conflict exists for the given entity and version.

        Reads the current active version and checks it against the expected values.

        Args:
            entity_version_key: Composite key for the entity.
            expected_version: The version to check against.
            expected_checksum: The checksum to check against.

        Returns:
            ConflictInfo if a conflict exists, None if the expected values match
            the current state.
        """
        active = self._version_store.read_active(entity_version_key)
        if active is None:
            if expected_version == 0:
                return None  # No entity expected, no entity exists — match
            return ConflictInfo(
                conflict_type="entity_not_found",
                expected_version=expected_version,
                actual_version=0,
                expected_checksum=expected_checksum,
                actual_checksum="",
                current_holder="",
                last_updated_at="",
            )

        conflicts: list[str] = []
        if active.version != expected_version:
            conflicts.append("version_mismatch")
        if active.checksum != expected_checksum:
            conflicts.append("checksum_mismatch")

        if not conflicts:
            return None

        return ConflictInfo(
            conflict_type=conflicts[0],
            expected_version=expected_version,
            actual_version=active.version,
            expected_checksum=expected_checksum,
            actual_checksum=active.checksum,
            current_holder=active.created_by,
            last_updated_at=active.created_at,
        )

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------

    @staticmethod
    def _compute_retry_delay(
        attempt: int,
        base_delay_ms: float,
        max_delay_ms: float,
        multiplier: float,
    ) -> float:
        """Compute exponential backoff delay with jitter.

        Args:
            attempt: Zero-based attempt number.
            base_delay_ms: Base delay in milliseconds.
            max_delay_ms: Maximum delay in milliseconds.
            multiplier: Backoff multiplier.

        Returns:
            Delay in seconds (float).
        """
        delay_ms = min(base_delay_ms * (multiplier ** attempt), max_delay_ms)
        jitter = random.uniform(0, delay_ms * 0.1)
        return (delay_ms + jitter) / 1000.0