-- Migration: 007_create_workflow_idempotency_table
-- Purpose: Idempotency key table for deduplicating workflow runs.
--          Each row represents a unique workflow invocation identified by
--          a deterministic idempotency key (e.g.
--          "{workflow_id}-scheduled-{schedule_slot}"). The table ensures
--          atomic key insertion — only one run can claim a given key.
-- Dependencies: None (new table)
-- Rollback: DROP TABLE IF EXISTS workflow_idempotency;

CREATE TABLE IF NOT EXISTS workflow_idempotency (
    idempotency_key    TEXT PRIMARY KEY,                                -- "{workflow_id}-{scope}-{schedule_slot}"
    pipeline_run_id    TEXT NOT NULL,                                   -- the run that claimed this key
    status             TEXT NOT NULL CHECK (status IN ('completed', 'failed', 'in_progress')),
    created_at         TIMESTAMP NOT NULL DEFAULT (datetime('now')),    -- ISO-8601
    completed_at       TIMESTAMP,                                      -- ISO-8601, NULL until status changes from in_progress
    result_summary     TEXT                                             -- JSON summary of WorkflowResult
);

-- Index for TTL-based cleanup: DELETE FROM workflow_idempotency WHERE created_at < datetime('now', '-' || ? || ' days')
CREATE INDEX IF NOT EXISTS idx_workflow_idempotency_created_at ON workflow_idempotency(created_at);

-- Index for status-based queries: used by check() to find completed runs
CREATE INDEX IF NOT EXISTS idx_workflow_idempotency_status ON workflow_idempotency(status);
</write_to_file>