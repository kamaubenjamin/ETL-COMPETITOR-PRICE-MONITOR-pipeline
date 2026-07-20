import re
from pathlib import Path


MIGRATION = Path("supabase/migrations/20260720140000_uat_identity_tenant_foundation.sql")


def test_identity_migration_is_schema_only_and_rls_protected():
    sql = MIGRATION.read_text(encoding="utf-8").lower()
    for table in ("public.app_tenants", "public.app_tenant_memberships"):
        assert f"alter table {table} enable row level security" in sql
    assert "to authenticated" in sql
    assert "auth.uid()" in sql
    assert "to anon" not in sql
    assert "revoke all on table public.app_tenants from anon" in sql
    assert "revoke all on table public.app_tenant_memberships from anon" in sql
    assert "unique (tenant_id, user_id)" in sql
    assert "role in ('owner', 'reviewer', 'viewer')" in sql
    assert "status in ('active', 'inactive')" in sql
    assert not re.search(r"\b(drop|truncate)\s+(table|schema)\b", sql)
    assert not re.search(r"\b(insert|update|delete)\s+(into|public\.)", sql)
    for forbidden in ("workflow_definitions", "documents", "password", "service_role", "@example"):
        assert forbidden not in sql


def test_identity_migration_contains_no_committed_bootstrap_identity_or_key():
    sql = MIGRATION.read_text(encoding="utf-8")
    assert not re.search(r"[0-9a-f]{8}-[0-9a-f]{4}-[1-5][0-9a-f]{3}-[89ab][0-9a-f]{3}-[0-9a-f]{12}", sql, re.I)
    assert not re.search(r"(?:sb_secret_|eyJ[A-Za-z0-9_-]{16,})", sql)
