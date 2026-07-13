ALTER TABLE documents ADD COLUMN tenant_id TEXT NOT NULL DEFAULT 'tenant-local';
ALTER TABLE documents ADD COLUMN workspace_id TEXT;
ALTER TABLE documents ADD COLUMN created_by TEXT;
ALTER TABLE documents ADD COLUMN updated_by TEXT;
ALTER TABLE documents ADD COLUMN owner_principal_id TEXT;
ALTER TABLE documents ADD COLUMN source_system TEXT;
ALTER TABLE documents ADD COLUMN access_tags_json TEXT NOT NULL DEFAULT '[]';
CREATE INDEX idx_documents_tenant_filters ON documents(tenant_id, status, document_type);
