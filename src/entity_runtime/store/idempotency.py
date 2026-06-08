"""EntityIdempotencyRegistry — SQLite-backed implementation for idempotent entity writes.

Prevents duplicate entity writes by tracking deterministic idempotency keys.
Keys are generated from entity_type, source_document_id, entity_natural_key,
workflow_run_id, and stage_name to ensure run-scoped uniqueness.
"""

from __future__ import annotations

import hashlib
import sqlite3
import threading
from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Optional


@dataclass(frozen=True, slots=True)
class IdempotencyResult:
    """Result of an idempotency check-and-record operation.

    Attributes:
        status: 'accepted' for first write, 'duplicate' for repeat.
        existing_version: The version that was already written (for duplicates).
        existing_run: The pipeline_run_id of the original write (for duplicates).
    """

    status: str
    """'accepted' | 'duplicate'."""

    existing_version: Optional[int] = None
    """The version that was already written (None for accepted)."""

    existing_run: Optional[str] = None
    """The pipeline_run_id of the original write (None for accepted)."""


class EntityIdempotencyRegistry:
    """SQLite-backed entity idempotency registry.

    Tracks deterministic idempotency keys to detect and reject duplicate writes.
    Supports TTL-based cleanup of expired keys.

    Uses atomic INSERT OR IGNORE for thread-safe check-and-record operations.
    """

    def __init__(self, db_path: str = "data/entity_version_store.db") -> None:
        self._db_path = db_path
        self._local = threading.local()
        self._lock = threading.RLock()

    # ------------------------------------------------------------------
    # Connection management
    # ------------------------------------------------------------------

    def _get_connection(self) -> sqlite3.Connection:
        """Get a thread-local SQLite connection."""
        if not hasattr(self._local, "conn") or self._local.conn is None:
            conn = sqlite3.connect(self._db_path, timeout=10)
            conn.execute("PRAGMA journal_mode=WAL;")
            conn.row_factory = sqlite3.Row
            self._local.conn = conn
        return self._local.conn

    def close(self) -> None:
        """Close the thread-local connection if open."""
        if hasattr(self._local, "conn") and self._local.conn is not None:
            self._local.conn.close()
            self._local.conn = None

    # ------------------------------------------------------------------
    # Key generation
    # ------------------------------------------------------------------

    def generate_key(
        self,
        entity_type: str,
        source_document_id: str,
        entity_natural_key: str,
        workflow_run_id: str,
        stage_name: str,
    ) -> str:
        """Generate a deterministic idempotency key.

        Uses SHA-256 of the concatenated components with 'entity_write:v1:' prefix.

        Args:
            entity_type: Entity class name (e.g. 'supplier').
            source_document_id: Document Runtime ID.
            entity_natural_key: Entity identifying fields (e.g. supplier name).
            workflow_run_id: ExecutionContext.pipeline_run_id.
            stage_name: Workflow stage name (e.g. 'entity_extract').

        Returns:
            A hex-encoded SHA-256 hash string with prefix.
        """
        raw = (
            f"{entity_type}:{source_document_id}:{entity_natural_key}:"
            f"{workflow_run_id}:{stage_name}"
        )
        key_hash = hashlib.sha256(raw.encode("utf-8")).hexdigest()
        return f"entity_write:v1:{key_hash}"

    # ------------------------------------------------------------------
    # Check-and-record
    # ------------------------------------------------------------------

    def check_and_record(
        self,
        idempotency_key: str,
        entity_version_key: str,
        new_version: int,
        pipeline_run_id: str,
    ) -> IdempotencyResult:
        """Atomically check and record an idempotency key.

        If the key doesn't exist, record it and return 'accepted'.
        If the key already exists, return 'duplicate' with existing details.

        Args:
            idempotency_key: The deterministic key for this write.
            entity_version_key: The entity being written.
            new_version: The version that would be written.
            pipeline_run_id: The run performing the write.

        Returns:
            IdempotencyResult with status 'accepted' or 'duplicate'.
        """
        conn = self._get_connection()
        now = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")

        with self._lock:
            # Check if key already exists
            cur = conn.execute(
                "SELECT status, version, pipeline_run_id FROM entity_idempotency "
                "WHERE idempotency_key = ?",
                (idempotency_key,),
            )
            row = cur.fetchone()

            if row is not None:
                # Key exists — it's a duplicate
                return IdempotencyResult(
                    status="duplicate",
                    existing_version=row["version"],
                    existing_run=row["pipeline_run_id"],
                )

            # Key doesn't exist — try to insert atomically
            try:
                conn.execute(
                    """INSERT INTO entity_idempotency
                       (idempotency_key, entity_version_key, version, pipeline_run_id,
                        status, created_at)
                       VALUES (?, ?, ?, ?, 'in_progress', ?)""",
                    (
                        idempotency_key,
                        entity_version_key,
                        new_version,
                        pipeline_run_id,
                        now,
                    ),
                )
                conn.commit()
                return IdempotencyResult(status="accepted")
            except sqlite3.IntegrityError:
                # Race condition — another thread inserted the same key
                conn.rollback()
                cur = conn.execute(
                    "SELECT status, version, pipeline_run_id FROM entity_idempotency "
                    "WHERE idempotency_key = ?",
                    (idempotency_key,),
                )
                row = cur.fetchone()
                if row is not None:
                    return IdempotencyResult(
                        status="duplicate",
                        existing_version=row["version"],
                        existing_run=row["pipeline_run_id"],
                    )
                return IdempotencyResult(status="accepted")

    # ------------------------------------------------------------------
    # Status query
    # ------------------------------------------------------------------

    def get_status(self, idempotency_key: str) -> Optional[IdempotencyResult]:
        """Query the status of an existing idempotency key.

        Args:
            idempotency_key: The deterministic key to query.

        Returns:
            IdempotencyResult if the key exists, None otherwise.
        """
        conn = self._get_connection()
        cur = conn.execute(
            "SELECT status, version, pipeline_run_id FROM entity_idempotency "
            "WHERE idempotency_key = ?",
            (idempotency_key,),
        )
        row = cur.fetchone()
        if row is None:
            return None
        return IdempotencyResult(
            status=row["status"],
            existing_version=row["version"],
            existing_run=row["pipeline_run_id"],
        )

    # ------------------------------------------------------------------
    # Status update
    # ------------------------------------------------------------------

    def mark_completed(self, idempotency_key: str) -> bool:
        """Mark an idempotency key as completed.

        Args:
            idempotency_key: The key to mark as completed.

        Returns:
            True if the key was updated, False if not found.
        """
        conn = self._get_connection()
        now = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
        cur = conn.execute(
            "UPDATE entity_idempotency SET status = 'completed', completed_at = ? "
            "WHERE idempotency_key = ? AND status = 'in_progress'",
            (now, idempotency_key),
        )
        conn.commit()
        return cur.rowcount > 0

    def mark_failed(self, idempotency_key: str) -> bool:
        """Mark an idempotency key as failed.

        Args:
            idempotency_key: The key to mark as failed.

        Returns:
            True if the key was updated, False if not found.
        """
        conn = self._get_connection()
        now = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
        cur = conn.execute(
            "UPDATE entity_idempotency SET status = 'failed', completed_at = ? "
            "WHERE idempotency_key = ? AND status = 'in_progress'",
            (now, idempotency_key),
        )
        conn.commit()
        return cur.rowcount > 0

    # ------------------------------------------------------------------
    # Cleanup
    # ------------------------------------------------------------------

    def cleanup(
        self,
        retention_days: int = 7,
        in_progress_ttl_minutes: int = 60,
        batch_size: int = 1000,
    ) -> int:
        """Clean up expired idempotency records.

        Deletes completed/failed records older than retention_days.
        Expires in-progress records older than in_progress_ttl_minutes.

        Args:
            retention_days: Delete completed/failed records older than this.
            in_progress_ttl_minutes: Expire in-progress records older than this.
            batch_size: Maximum number of records to delete in one cycle.

        Returns:
            Number of records cleaned up.
        """
        conn = self._get_connection()
        now = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
        total_removed = 0

        with self._lock:
            # 1. Expire in-progress records beyond TTL
            cur = conn.execute(
                "UPDATE entity_idempotency SET status = 'expired' "
                "WHERE status = 'in_progress' "
                "AND created_at < datetime('now', ? || ' minutes')",
                (f"-{in_progress_ttl_minutes}",),
            )
            expired_count = cur.rowcount

            # 2. Delete completed/failed records older than retention
            cur = conn.execute(
                "DELETE FROM entity_idempotency "
                "WHERE status IN ('completed', 'failed') "
                "AND created_at < datetime('now', ? || ' days') "
                "LIMIT ?",
                (f"-{retention_days}", batch_size),
            )
            deleted_count = cur.rowcount

            # 3. Delete expired records older than retention
            cur = conn.execute(
                "DELETE FROM entity_idempotency "
                "WHERE status = 'expired' "
                "AND created_at < datetime('now', ? || ' days') "
                "LIMIT ?",
                (f"-{retention_days}", batch_size),
            )
            expired_deleted = cur.rowcount

            conn.commit()
            total_removed = expired_count + deleted_count + expired_deleted

        return total_removed