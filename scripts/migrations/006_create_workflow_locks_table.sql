-- Migration: 006_create_workflow_locks_table
-- Purpose: Distributed lock table for workflow execution coordination.
--          Each row represents an active or expired lock for a single
--          workflow_id. The table uses UPSERT semantics: if a lock exists
--          and is NOT expired, the INSERT conflicts and does nothing; if
--          the lock IS expired, the UPSERT replaces it with a new lease.
-- Dependencies: None (new table)
-- Rollback: DROP TABLE IF EXISTS workflow_locks;

CREATE TABLE IF NOT EXISTS workflow_locks (
    lock_id            TEXT PRIMARY KEY,                                -- workflow_id
    holder_id          TEXT NOT NULL,                                   -- hostname-pid-pipeline_run_id
    acquired_at        TIMESTAMP NOT NULL DEFAULT (datetime('now')),    -- ISO-8601
    expires_at         TIMESTAMP NOT NULL,                              -- ISO-8601 (acquired_at + lease_duration_s)
    lease_duration_s   INTEGER NOT NULL DEFAULT 300,                    -- lease TTL in seconds
    hostname           TEXT NOT NULL,                                   -- socket.gethostname()
    pid                INTEGER,                                         -- os.getpid()
    refresh_count      INTEGER NOT NULL DEFAULT 0,                      -- number of lease refreshes
    last_refreshed_at  TIMESTAMP NOT NULL DEFAULT (datetime('now'))     -- last successful refresh
);

-- Index for stale lock cleanup: DELETE FROM workflow_locks WHERE expires_at < datetime('now')
CREATE INDEX IF NOT EXISTS idx_workflow_locks_expires_at ON workflow_locks(expires_at);

-- Index for lock holder lookup: used in release() and refresh() to verify holder identity
CREATE INDEX IF NOT EXISTS idx_workflow_locks_holder_id ON workflow_locks(holder_id);
</write_to_file>