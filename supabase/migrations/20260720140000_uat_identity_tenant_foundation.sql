-- v0.21 Phase 5: minimal UAT identity and tenant-membership authority.
-- Schema only. UAT users, tenants, and memberships are owner-created separately.

create table if not exists public.app_tenants (
    id uuid primary key default gen_random_uuid(),
    slug text not null unique,
    name text not null,
    status text not null default 'active',
    created_at timestamptz not null default now(),
    updated_at timestamptz not null default now(),
    constraint app_tenants_slug_format check (slug = lower(slug) and slug ~ '^[a-z0-9][a-z0-9-]{0,62}$'),
    constraint app_tenants_name_length check (char_length(name) between 1 and 128),
    constraint app_tenants_status_allowed check (status in ('active', 'inactive'))
);

create table if not exists public.app_tenant_memberships (
    id uuid primary key default gen_random_uuid(),
    tenant_id uuid not null references public.app_tenants(id) on delete restrict,
    user_id uuid not null references auth.users(id) on delete restrict,
    role text not null,
    status text not null default 'active',
    created_at timestamptz not null default now(),
    updated_at timestamptz not null default now(),
    constraint app_tenant_memberships_tenant_user_unique unique (tenant_id, user_id),
    constraint app_tenant_memberships_role_allowed check (role in ('owner', 'reviewer', 'viewer')),
    constraint app_tenant_memberships_status_allowed check (status in ('active', 'inactive'))
);

create index if not exists app_tenant_memberships_user_status_idx
    on public.app_tenant_memberships (user_id, status);

alter table public.app_tenants enable row level security;
alter table public.app_tenant_memberships enable row level security;

revoke all on table public.app_tenants from anon;
revoke all on table public.app_tenant_memberships from anon;
revoke insert, update, delete, truncate, references, trigger on table public.app_tenants from authenticated;
revoke insert, update, delete, truncate, references, trigger on table public.app_tenant_memberships from authenticated;
grant select on table public.app_tenants to authenticated;
grant select on table public.app_tenant_memberships to authenticated;

do $policy$
begin
    if not exists (
        select 1 from pg_policies
        where schemaname = 'public'
          and tablename = 'app_tenant_memberships'
          and policyname = 'memberships_select_own_active'
    ) then
        create policy memberships_select_own_active
            on public.app_tenant_memberships
            for select
            to authenticated
            using ((select auth.uid()) = user_id and status = 'active');
    end if;

    if not exists (
        select 1 from pg_policies
        where schemaname = 'public'
          and tablename = 'app_tenants'
          and policyname = 'tenants_select_through_active_membership'
    ) then
        create policy tenants_select_through_active_membership
            on public.app_tenants
            for select
            to authenticated
            using (
                status = 'active'
                and exists (
                    select 1
                    from public.app_tenant_memberships membership
                    where membership.tenant_id = app_tenants.id
                      and membership.user_id = (select auth.uid())
                      and membership.status = 'active'
                )
            );
    end if;
end
$policy$;
