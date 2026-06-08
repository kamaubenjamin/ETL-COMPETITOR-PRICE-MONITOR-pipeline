-- ============================================================
-- Migration 008: Create Entity Version Store
-- 
-- Creates 4 tables for entity concurrency hardening:
--   1. entity_versions       — append-only version history
--   2. entity_leases         — execution lease management
--   3. entity_idempotency    — duplicate write detection
--   4. entity_conflict_log   — audit trail for concurrency conflicts
--
-- Rollback: DROP TABLE IF EXISTS entity_versions, entity_leases,
--   entity_idempotency, entity_conflict_log;
-- ============================================================

-- ============================================================
-- Table 1: entity_versions — append-only version history
-- ============================================================

CREATE TABLE IF NOT EXISTS entity_versions (
    -- Identity
    entity_version_key   TEXT NOT NULL,         -- "{type}:{doc_id}:{natural_key}"
    entity_type          TEXT NOT NULL,          -- "supplier" | "customer" | "line_item" | "document_reference" | "document_financials"
    entity_id            TEXT NOT NULL,          -- Natural key within type
    version              INTEGER NOT NULL,       -- Monotonic version number

    -- State
    state                TEXT NOT NULL DEFAULT 'active',  -- "active" | "superseded" | "archived"

    -- Data
    data                 TEXT NOT NULL,          -- JSON-serialized entity data
    checksum             TEXT NOT NULL,          -- SHA-256 hex digest of data
    previous_checksum    TEXT NOT NULL DEFAULT '',  -- SHA-256 of version-1 data

    -- Provenance
    created_at           TEXT NOT NULL,          -- ISO-8601 timestamp
    created_by           TEXT NOT NULL,          -- pipeline_run_id or "system"
    source_document_id   TEXT NOT NULL DEFAULT '',  -- Document that produced this version

    -- Constraints
    PRIMARY KEY (entity_version_key, version)
);

-- Current version index (fast lookup for active entities)
CREATE INDEX IF NOT EXISTS idx_entity_versions_active
    ON entity_versions (entity_version_key, version DESC)
    WHERE state = 'active';

-- Entity type query index
CREATE INDEX IF NOT EXISTS idx_entity_versions_type
    ON entity_versions (entity_type, state);

-- Source document provenance index
CREATE INDEX IF NOT EXISTS idx_entity_versions_source
    ON entity_versions (source_document_id);

-- ============================================================
-- Table 2: entity_leases — execution lease management
-- ============================================================

CREATE TABLE IF NOT EXISTS entity_leases (
    entity_version_key   TEXT PRIMARY KEY,      -- Reference to entity
    holder_id            TEXT NOT NULL,          -- "{hostname}-{pid}-{pipeline_run_id}"
    acquired_at          TEXT NOT NULL,          -- ISO-8601 timestamp
    expires_at           TEXT NOT NULL,          -- ISO-8601 timestamp (acquired_at + lease_duration_s)
    lease_duration_s     INTEGER NOT NULL DEFAULT 120,
    last_refreshed_at    TEXT NOT NULL,          -- ISO-8601 timestamp
    refresh_count        INTEGER NOT NULL DEFAULT 0,
    hostname             TEXT NOT NULL DEFAULT '',
    pid                  INTEGER NOT NULL DEFAULT 0
);

-- Expired lease index (for crash recovery scanning)
CREATE INDEX IF NOT EXISTS idx_entity_leases_expired
    ON entity_leases (expires_at)
    WHERE expires_at < CURRENT_TIMESTAMP;

-- ============================================================
-- Table 3: entity_idempotency — duplicate write detection
-- ============================================================

CREATE TABLE IF NOT EXISTS entity_idempotency (
    idempotency_key      TEXT PRIMARY KEY,      -- SHA-256 of key components
    entity_version_key   TEXT NOT NULL,          -- Entity being written
    version              INTEGER NOT NULL,       -- Version that was written
    pipeline_run_id      TEXT NOT NULL,          -- Run that performed the write
    status               TEXT NOT NULL DEFAULT 'in_progress',  -- "in_progress" | "completed" | "failed" | "expired"
    created_at           TEXT NOT NULL,          -- ISO-8601 timestamp
    completed_at         TEXT                    -- ISO-8601 timestamp (nullable)
);

-- Cleanup index
CREATE INDEX IF NOT EXISTS idx_entity_idempotency_cleanup
    ON entity_idempotency (status, created_at);

-- ============================================================
-- Table 4: entity_conflict_log — audit trail for concurrency conflicts
-- ============================================================

CREATE TABLE IF NOT EXISTS entity_conflict_log (
    conflict_id          INTEGER PRIMARY KEY AUTOINCREMENT,
    entity_version_key   TEXT NOT NULL,
    conflict_type        TEXT NOT NULL,          -- "version_mismatch" | "checksum_mismatch" | "lease_busy" | "deadlock"
    attempted_version    INTEGER NOT NULL,
    current_version      INTEGER NOT NULL,
    attempted_by         TEXT NOT NULL,          -- pipeline_run_id
    current_holder       TEXT NOT NULL DEFAULT '',  -- pipeline_run_id holding current version
    resolution           TEXT NOT NULL DEFAULT '',  -- "retry" | "escalate" | "abort"
    created_at           TEXT NOT NULL
);

-- Conflict query index
CREATE INDEX IF NOT EXISTS idx_entity_conflict_log_entity
    ON entity_conflict_log (entity_version_key, created_at DESC);