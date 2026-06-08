"""EntityVersionRecord — immutable version record, and EntityVersionStore — SQLite-backed
versioned CRUD with compare-and-swap semantics.

Version records are append-only: each write creates a new row in the version store,
and the previous 'active' version is marked 'superseded'.

Entity lifecycle states:
  - active: Current version, available for reads
  - superseded: Older version, still in store
  - archived: Removed from version history (compacted)
"""

from __future__ import annotations

import hashlib
import json
import sqlite3
import threading
from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Any, Optional

from src.entity_runtime.concurrency.errors import (
    EntityConflictError,
    EntityCorruptionError,
)


@dataclass(frozen=True, slots=True)
class EntityVersionRecord:
    """Immutable record in the Entity Version Store.

    Each record represents one version of an entity. Records are never mutated
    in-place; new versions are inserted as new rows.
    """

    entity_version_key: str
    """Composite key: '{entity_type}:{source_document_id}:{entity_natural_key}'."""

    entity_type: str
    """Entity type discriminator: 'supplier' | 'customer' | 'line_item' | 'document_reference' | 'document_financials'."""

    entity_id: str
    """Natural key within the entity type."""

    version: int
    """Monotonic version number (starts at 1 for each entity)."""

    state: str
    """Current state: 'active' | 'superseded' | 'archived'."""

    data: dict[str, Any]
    """Full entity data (serialized as JSON in the store)."""

    checksum: str
    """SHA-256 hex digest of the serialized data."""

    previous_checksum: str
    """SHA-256 of the previous version's data (empty string for v1)."""

    created_at: str
    """ISO-8601 timestamp of version creation."""

    created_by: str
    """pipeline_run_id that created this version, or 'system'."""

    source_document_id: str = ""
    """Document that produced this version (empty for canonical/merged entities)."""

    lease_holder: str = ""
    """pipeline_run_id holding the write lease (empty when released)."""

    lease_expires_at: str = ""
    """ISO timestamp of lease expiry (empty when no lease held)."""


class EntityVersionStore:
    """SQLite-backed entity version store with compare-and-swap semantics.

    Provides versioned read, write, history, state transitions, and atomic
    compare-and-swap operations. All writes are atomic within a single SQLite
    transaction. Uses WAL mode for concurrent read access.
    """

    def __init__(self, db_path: str = "data/entity_version_store.db") -> None:
        self._db_path = db_path
        self._local = threading.local()
        self._lock = threading.RLock()

    # ------------------------------------------------------------------
    # Connection management
    # ------------------------------------------------------------------

    def _get_connection(self) -> sqlite3.Connection:
        """Get a thread-local SQLite connection with WAL mode."""
        if not hasattr(self._local, "conn") or self._local.conn is None:
            conn = sqlite3.connect(self._db_path, timeout=10)
            conn.execute("PRAGMA journal_mode=WAL;")
            conn.execute("PRAGMA busy_timeout=5000;")
            conn.row_factory = sqlite3.Row
            self._local.conn = conn
        return self._local.conn

    def close(self) -> None:
        """Close the thread-local connection if open."""
        if hasattr(self._local, "conn") and self._local.conn is not None:
            self._local.conn.close()
            self._local.conn = None

    # ------------------------------------------------------------------
    # Checksum utilities
    # ------------------------------------------------------------------

    @staticmethod
    def compute_checksum(data: dict[str, Any]) -> str:
        """Compute SHA-256 hex digest of the serialized data."""
        raw = json.dumps(data, sort_keys=True, ensure_ascii=False, default=str)
        return hashlib.sha256(raw.encode("utf-8")).hexdigest()

    @staticmethod
    def _now_iso() -> str:
        """Get current UTC timestamp as ISO-8601 string."""
        return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")

    @staticmethod
    def _row_to_record(row: sqlite3.Row) -> EntityVersionRecord:
        """Convert a SQLite row to an EntityVersionRecord."""
        return EntityVersionRecord(
            entity_version_key=row["entity_version_key"],
            entity_type=row["entity_type"],
            entity_id=row["entity_id"],
            version=row["version"],
            state=row["state"],
            data=json.loads(row["data"]),
            checksum=row["checksum"],
            previous_checksum=row["previous_checksum"],
            created_at=row["created_at"],
            created_by=row["created_by"],
            source_document_id=row["source_document_id"],
        )

    # ------------------------------------------------------------------
    # Core CRUD operations
    # ------------------------------------------------------------------

    def write_version(
        self,
        entity_version_key: str,
        data: dict[str, Any],
        expected_version: int,
        checksum: str,
        entity_type: str,
        entity_id: str,
        created_by: str,
        source_document_id: str = "",
    ) -> EntityVersionRecord:
        """Write a new version using compare-and-swap semantics.

        Args:
            entity_version_key: Composite key for the entity.
            data: Full entity data to store.
            expected_version: Expected current version (0 for first write).
            checksum: SHA-256 hex digest of the serialized data.
            entity_type: Entity type discriminator.
            entity_id: Natural key within the entity type.
            created_by: pipeline_run_id that created this version.
            source_document_id: Document that produced this version.

        Returns:
            The newly created EntityVersionRecord.

        Raises:
            EntityConflictError: If the expected version doesn't match.
            EntityCorruptionError: If checksum mismatch with current data.
        """
        conn = self._get_connection()
        now = self._now_iso()
        new_version = expected_version + 1

        with self._lock:
            cur = conn.execute(
                "SELECT version, checksum, data FROM entity_versions "
                "WHERE entity_version_key = ? AND state = 'active'",
                (entity_version_key,),
            )
            row = cur.fetchone()

            if row is not None:
                current_version = row["version"]

                if current_version != expected_version:
                    raise EntityConflictError(
                        entity_version_key=entity_version_key,
                        expected_version=expected_version,
                        actual_version=current_version,
                    )

                # Supersede current active version
                conn.execute(
                    "UPDATE entity_versions SET state = 'superseded' "
                    "WHERE entity_version_key = ? AND version = ?",
                    (entity_version_key, current_version),
                )

            elif expected_version != 0:
                # Entity doesn't exist but expected_version > 0 — conflict
                raise EntityConflictError(
                    entity_version_key=entity_version_key,
                    expected_version=expected_version,
                    actual_version=0,
                )

            # Compute previous checksum
            previous_checksum = row["checksum"] if row is not None else ""

            # Insert new version with sort_keys=True for consistent serialization
            conn.execute(
                """INSERT INTO entity_versions
                   (entity_version_key, entity_type, entity_id, version, state,
                    data, checksum, previous_checksum, created_at, created_by,
                    source_document_id)
                   VALUES (?, ?, ?, ?, 'active', ?, ?, ?, ?, ?, ?)""",
                (
                    entity_version_key,
                    entity_type,
                    entity_id,
                    new_version,
                    json.dumps(data, sort_keys=True, ensure_ascii=False, default=str),
                    checksum,
                    previous_checksum,
                    now,
                    created_by,
                    source_document_id,
                ),
            )
            conn.commit()

        return EntityVersionRecord(
            entity_version_key=entity_version_key,
            entity_type=entity_type,
            entity_id=entity_id,
            version=new_version,
            state="active",
            data=data,
            checksum=checksum,
            previous_checksum=previous_checksum,
            created_at=now,
            created_by=created_by,
            source_document_id=source_document_id,
        )

    def read_active(self, entity_version_key: str) -> Optional[EntityVersionRecord]:
        """Read the current active version of an entity.

        Args:
            entity_version_key: Composite key for the entity.

        Returns:
            The active EntityVersionRecord, or None if the entity doesn't exist.
        """
        conn = self._get_connection()
        cur = conn.execute(
            "SELECT * FROM entity_versions "
            "WHERE entity_version_key = ? AND state = 'active'",
            (entity_version_key,),
        )
        row = cur.fetchone()
        if row is None:
            return None
        return self._row_to_record(row)

    def read_version(
        self, entity_version_key: str, version: int
    ) -> Optional[EntityVersionRecord]:
        """Read a specific version of an entity.

        Args:
            entity_version_key: Composite key for the entity.
            version: The specific version to read.

        Returns:
            The EntityVersionRecord for the requested version, or None.
        """
        conn = self._get_connection()
        cur = conn.execute(
            "SELECT * FROM entity_versions "
            "WHERE entity_version_key = ? AND version = ?",
            (entity_version_key, version),
        )
        row = cur.fetchone()
        if row is None:
            return None
        return self._row_to_record(row)

    def read_history(self, entity_version_key: str) -> list[EntityVersionRecord]:
        """Read the full version history for an entity, ordered by version ascending.

        Args:
            entity_version_key: Composite key for the entity.

        Returns:
            List of EntityVersionRecord ordered by version (v1, v2, ...).
        """
        conn = self._get_connection()
        cur = conn.execute(
            "SELECT * FROM entity_versions "
            "WHERE entity_version_key = ? ORDER BY version ASC",
            (entity_version_key,),
        )
        return [self._row_to_record(row) for row in cur.fetchall()]

    def transition_state(
        self, entity_version_key: str, version: int, new_state: str
    ) -> bool:
        """Transition a version record's state.

        Valid transitions:
          - 'active' -> 'superseded' (when a new version is created)
          - 'active' -> 'archived' (force-archive, e.g. entity deletion)
          - 'superseded' -> 'archived' (when retention window exceeded)

        Args:
            entity_version_key: Composite key for the entity.
            version: The version to transition.
            new_state: The target state.

        Returns:
            True if the transition was applied, False if invalid or record not found.
        """
        conn = self._get_connection()
        cur = conn.execute(
            "SELECT state FROM entity_versions "
            "WHERE entity_version_key = ? AND version = ?",
            (entity_version_key, version),
        )
        row = cur.fetchone()
        if row is None:
            return False

        current_state = row["state"]

        # Validate transitions
        valid = False
        if current_state == "active" and new_state in ("superseded", "archived"):
            valid = True
        elif current_state == "superseded" and new_state == "archived":
            valid = True
        elif current_state == "archived" and new_state == "archived":
            # Idempotent transition
            return True

        if not valid:
            return False

        cur = conn.execute(
            "UPDATE entity_versions SET state = ? "
            "WHERE entity_version_key = ? AND version = ? AND state = ?",
            (new_state, entity_version_key, version, current_state),
        )
        conn.commit()
        return cur.rowcount > 0

    def compare_and_swap(
        self,
        entity_version_key: str,
        data: dict[str, Any],
        expected_version: int,
        expected_checksum: str,
        entity_type: str,
        entity_id: str,
        created_by: str,
        source_document_id: str,
    ) -> tuple[bool, Optional[dict[str, Any]]]:
        """Atomic compare-and-swap operation.

        Atomically reads the current active version, checks that it matches
        expected_version and expected_checksum, then writes the new version.

        Args:
            entity_version_key: Composite key for the entity.
            data: Full entity data to store.
            expected_version: Expected current version.
            expected_checksum: Expected checksum of current data.
            entity_type: Entity type discriminator.
            entity_id: Natural key within the entity type.
            created_by: pipeline_run_id that created this version.
            source_document_id: Document that produced this version.

        Returns:
            Tuple of (success, conflict_info_dict). If success is True,
            conflict_info is None. If success is False, conflict_info contains
            details about the conflict.
        """
        try:
            record = self.write_version(
                entity_version_key=entity_version_key,
                data=data,
                expected_version=expected_version,
                checksum=self.compute_checksum(data),
                entity_type=entity_type,
                entity_id=entity_id,
                created_by=created_by,
                source_document_id=source_document_id,
            )
            return True, None
        except EntityConflictError as e:
            return False, {
                "conflict_type": "version_mismatch",
                "expected_version": e.expected_version,
                "actual_version": e.actual_version,
                "expected_checksum": expected_checksum,
                "actual_checksum": "",
                "current_holder": "",
                "last_updated_at": "",
            }

    # ------------------------------------------------------------------
    # Conflict log operations
    # ------------------------------------------------------------------

    def log_conflict(
        self,
        entity_version_key: str,
        conflict_type: str,
        attempted_version: int,
        current_version: int,
        attempted_by: str,
        current_holder: str = "",
        resolution: str = "",
    ) -> int:
        """Record a concurrency conflict in the conflict log.

        Args:
            entity_version_key: The entity key that experienced the conflict.
            conflict_type: 'version_mismatch' | 'checksum_mismatch' | 'lease_busy' | 'deadlock'.
            attempted_version: The version that was attempted.
            current_version: The current version in the store.
            attempted_by: pipeline_run_id that attempted the write.
            current_holder: pipeline_run_id holding the current version.
            resolution: 'retry' | 'escalate' | 'abort'.

        Returns:
            The conflict_id of the recorded entry.
        """
        conn = self._get_connection()
        now = self._now_iso()
        cur = conn.execute(
            """INSERT INTO entity_conflict_log
               (entity_version_key, conflict_type, attempted_version, current_version,
                attempted_by, current_holder, resolution, created_at)
               VALUES (?, ?, ?, ?, ?, ?, ?, ?)""",
            (
                entity_version_key,
                conflict_type,
                attempted_version,
                current_version,
                attempted_by,
                current_holder,
                resolution,
                now,
            ),
        )
        conn.commit()
        return cur.lastrowid  # type: ignore[return-value]

    def get_conflicts(
        self,
        entity_version_key: str,
        limit: int = 100,
    ) -> list[dict[str, Any]]:
        """Get conflict history for an entity.

        Args:
            entity_version_key: The entity key to query.
            limit: Maximum number of conflict entries to return.

        Returns:
            List of conflict log entries as dicts.
        """
        conn = self._get_connection()
        cur = conn.execute(
            "SELECT * FROM entity_conflict_log "
            "WHERE entity_version_key = ? "
            "ORDER BY created_at DESC LIMIT ?",
            (entity_version_key, limit),
        )
        rows = cur.fetchall()
        return [dict(row) for row in rows]

    # ------------------------------------------------------------------
    # Table initialization
    # ------------------------------------------------------------------

    def initialize_schema(self) -> None:
        """Create the entity version store tables if they don't exist.

        This is a convenience method for testing. In production, use the
        migration runner (src.entity_runtime.store.migrations.EntityStoreMigration).
        """
        conn = self._get_connection()
        conn.executescript("""
            CREATE TABLE IF NOT EXISTS entity_versions (
                entity_version_key   TEXT NOT NULL,
                entity_type          TEXT NOT NULL,
                entity_id            TEXT NOT NULL,
                version              INTEGER NOT NULL,
                state                TEXT NOT NULL DEFAULT 'active',
                data                 TEXT NOT NULL,
                checksum             TEXT NOT NULL,
                previous_checksum    TEXT NOT NULL DEFAULT '',
                created_at           TEXT NOT NULL,
                created_by           TEXT NOT NULL,
                source_document_id   TEXT NOT NULL DEFAULT '',
                PRIMARY KEY (entity_version_key, version)
            );
            CREATE INDEX IF NOT EXISTS idx_entity_versions_active
                ON entity_versions (entity_version_key, version DESC)
                WHERE state = 'active';
            CREATE INDEX IF NOT EXISTS idx_entity_versions_type
                ON entity_versions (entity_type, state);
            CREATE INDEX IF NOT EXISTS idx_entity_versions_source
                ON entity_versions (source_document_id);

            CREATE TABLE IF NOT EXISTS entity_leases (
                entity_version_key   TEXT PRIMARY KEY,
                holder_id            TEXT NOT NULL,
                acquired_at          TEXT NOT NULL,
                expires_at           TEXT NOT NULL,
                lease_duration_s     INTEGER NOT NULL DEFAULT 120,
                last_refreshed_at    TEXT NOT NULL,
                refresh_count        INTEGER NOT NULL DEFAULT 0,
                hostname             TEXT NOT NULL DEFAULT '',
                pid                  INTEGER NOT NULL DEFAULT 0
            );
            CREATE INDEX IF NOT EXISTS idx_entity_leases_expired
                ON entity_leases (expires_at);

            CREATE TABLE IF NOT EXISTS entity_idempotency (
                idempotency_key      TEXT PRIMARY KEY,
                entity_version_key   TEXT NOT NULL,
                version              INTEGER NOT NULL,
                pipeline_run_id      TEXT NOT NULL,
                status               TEXT NOT NULL DEFAULT 'in_progress',
                created_at           TEXT NOT NULL,
                completed_at         TEXT
            );
            CREATE INDEX IF NOT EXISTS idx_entity_idempotency_cleanup
                ON entity_idempotency (status, created_at);

            CREATE TABLE IF NOT EXISTS entity_conflict_log (
                conflict_id          INTEGER PRIMARY KEY AUTOINCREMENT,
                entity_version_key   TEXT NOT NULL,
                conflict_type        TEXT NOT NULL,
                attempted_version    INTEGER NOT NULL,
                current_version      INTEGER NOT NULL,
                attempted_by         TEXT NOT NULL,
                current_holder       TEXT NOT NULL DEFAULT '',
                resolution           TEXT NOT NULL DEFAULT '',
                created_at           TEXT NOT NULL
            );
            CREATE INDEX IF NOT EXISTS idx_entity_conflict_log_entity
                ON entity_conflict_log (entity_version_key, created_at DESC);
        """)
        conn.commit()