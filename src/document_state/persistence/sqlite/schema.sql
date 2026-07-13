CREATE TABLE documents (
    document_id TEXT PRIMARY KEY,
    filename TEXT NOT NULL,
    document_type TEXT NOT NULL,
    status TEXT NOT NULL,
    confidence REAL NOT NULL,
    current_stage TEXT NOT NULL,
    received_at TEXT NOT NULL,
    created_at TEXT NOT NULL,
    updated_at TEXT NOT NULL,
    version INTEGER NOT NULL,
    metadata_json TEXT NOT NULL
);
CREATE INDEX idx_documents_list ON documents(received_at, document_id);
CREATE INDEX idx_documents_filters ON documents(status, document_type);

CREATE TABLE document_lifecycle_events (
    event_id TEXT PRIMARY KEY,
    document_id TEXT NOT NULL,
    status TEXT NOT NULL,
    occurred_at TEXT NOT NULL,
    source_runtime TEXT NOT NULL,
    source_stage TEXT NOT NULL,
    reason_code TEXT,
    metadata_json TEXT NOT NULL,
    idempotency_key TEXT NOT NULL UNIQUE,
    content_hash TEXT NOT NULL
);
CREATE INDEX idx_lifecycle_list ON document_lifecycle_events(document_id, occurred_at, event_id);
CREATE INDEX idx_lifecycle_filters ON document_lifecycle_events(document_id, status);

CREATE TABLE processing_snapshots (
    snapshot_id TEXT PRIMARY KEY,
    document_id TEXT NOT NULL,
    workflow_run_id TEXT NOT NULL,
    stage TEXT NOT NULL,
    status TEXT NOT NULL,
    started_at TEXT NOT NULL,
    updated_at TEXT NOT NULL,
    completed_at TEXT,
    duration_ms INTEGER,
    version INTEGER NOT NULL,
    metadata_json TEXT NOT NULL
);
CREATE INDEX idx_processing_list ON processing_snapshots(document_id, updated_at, stage, snapshot_id);
CREATE INDEX idx_processing_filters ON processing_snapshots(document_id, status, workflow_run_id);

CREATE TABLE validation_issues (
    issue_id TEXT PRIMARY KEY,
    document_id TEXT NOT NULL,
    validation_run_id TEXT NOT NULL,
    severity TEXT NOT NULL,
    field TEXT NOT NULL,
    rule_id TEXT NOT NULL,
    code TEXT NOT NULL,
    message TEXT NOT NULL,
    occurred_at TEXT NOT NULL,
    metadata_json TEXT NOT NULL,
    idempotency_key TEXT NOT NULL UNIQUE,
    content_hash TEXT NOT NULL
);
CREATE INDEX idx_validation_list ON validation_issues(document_id, severity, field, rule_id, issue_id);
CREATE INDEX idx_validation_filters ON validation_issues(document_id, severity, rule_id);

CREATE TABLE matching_summaries (
    match_id TEXT PRIMARY KEY,
    document_id TEXT NOT NULL,
    matching_run_id TEXT NOT NULL,
    entity_type TEXT NOT NULL,
    candidate_id TEXT NOT NULL,
    confidence REAL NOT NULL,
    status TEXT NOT NULL,
    occurred_at TEXT NOT NULL,
    metadata_json TEXT NOT NULL,
    idempotency_key TEXT NOT NULL UNIQUE,
    content_hash TEXT NOT NULL
);
CREATE INDEX idx_matching_list ON matching_summaries(document_id, confidence DESC, candidate_id, match_id);
CREATE INDEX idx_matching_filters ON matching_summaries(document_id, status, entity_type);

CREATE TABLE review_summaries (
    review_case_id TEXT PRIMARY KEY,
    document_id TEXT NOT NULL,
    reason_code TEXT NOT NULL,
    priority TEXT NOT NULL,
    status TEXT NOT NULL,
    created_at TEXT NOT NULL,
    updated_at TEXT NOT NULL,
    assigned_reviewer_id TEXT,
    correction_count INTEGER NOT NULL,
    decision_code TEXT,
    reprocess_state TEXT,
    version INTEGER NOT NULL,
    metadata_json TEXT NOT NULL
);
CREATE INDEX idx_reviews_list ON review_summaries(priority DESC, created_at, review_case_id);
CREATE INDEX idx_reviews_filters ON review_summaries(status, priority);

CREATE TABLE correction_summaries (
    correction_id TEXT PRIMARY KEY,
    review_case_id TEXT NOT NULL,
    document_id TEXT NOT NULL,
    field_path TEXT NOT NULL,
    operation TEXT NOT NULL,
    reason_code TEXT NOT NULL,
    actor_id TEXT NOT NULL,
    occurred_at TEXT NOT NULL,
    source_stage TEXT NOT NULL,
    metadata_json TEXT NOT NULL,
    idempotency_key TEXT NOT NULL UNIQUE,
    content_hash TEXT NOT NULL
);
CREATE INDEX idx_corrections_list ON correction_summaries(review_case_id, occurred_at, correction_id);

CREATE TABLE reprocess_plans (
    plan_id TEXT PRIMARY KEY,
    review_case_id TEXT NOT NULL,
    document_id TEXT NOT NULL,
    requested_from_stage TEXT NOT NULL,
    requested_target_stage TEXT NOT NULL,
    invalidated_artifact_count INTEGER NOT NULL,
    retained_artifact_count INTEGER NOT NULL,
    reason_code TEXT NOT NULL,
    requested_by TEXT NOT NULL,
    created_at TEXT NOT NULL,
    mode TEXT NOT NULL,
    metadata_json TEXT NOT NULL,
    idempotency_key TEXT NOT NULL UNIQUE,
    content_hash TEXT NOT NULL
);
CREATE INDEX idx_reprocess_list ON reprocess_plans(review_case_id, created_at DESC, plan_id);

CREATE TABLE workflow_runs (
    run_id TEXT PRIMARY KEY,
    workflow_name TEXT NOT NULL,
    status TEXT NOT NULL,
    started_at TEXT NOT NULL,
    created_at TEXT NOT NULL,
    updated_at TEXT NOT NULL,
    completed_at TEXT,
    duration_ms INTEGER,
    current_stage TEXT,
    stage_count INTEGER NOT NULL,
    succeeded_stage_count INTEGER NOT NULL,
    failed_stage_count INTEGER NOT NULL,
    version INTEGER NOT NULL,
    metadata_json TEXT NOT NULL
);
CREATE INDEX idx_workflow_runs_list ON workflow_runs(started_at DESC, run_id);
CREATE INDEX idx_workflow_runs_filters ON workflow_runs(status, workflow_name);

CREATE TABLE audit_events (
    event_id TEXT PRIMARY KEY,
    event_type TEXT NOT NULL,
    actor_id TEXT NOT NULL,
    occurred_at TEXT NOT NULL,
    document_id TEXT,
    review_case_id TEXT,
    workflow_run_id TEXT,
    metadata_json TEXT NOT NULL,
    idempotency_key TEXT NOT NULL UNIQUE,
    content_hash TEXT NOT NULL
);
CREATE INDEX idx_audit_list ON audit_events(occurred_at DESC, event_id);
CREATE INDEX idx_audit_filters ON audit_events(event_type, document_id, review_case_id);
