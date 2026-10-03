-- AI Agent Content Manager SaaS
-- Run once in Supabase SQL Editor.

create extension if not exists pgcrypto;

create table if not exists public.tenants (
  id uuid primary key default gen_random_uuid(),
  name text not null default 'Новый магазин',
  slug text unique,
  owner_user_id uuid not null references auth.users(id) on delete cascade,
  plan text not null default 'trial',
  status text not null default 'active',
  created_at timestamptz not null default now()
);

create table if not exists public.memberships (
  user_id uuid not null references auth.users(id) on delete cascade,
  tenant_id uuid not null references public.tenants(id) on delete cascade,
  role text not null default 'owner',
  created_at timestamptz not null default now(),
  primary key (user_id, tenant_id)
);

create table if not exists public.subscriptions (
  id uuid primary key default gen_random_uuid(),
  tenant_id uuid not null unique references public.tenants(id) on delete cascade,
  provider text,
  provider_customer_id text,
  provider_subscription_id text,
  plan text not null default 'trial',
  status text not null default 'trialing',
  current_period_end timestamptz,
  created_at timestamptz not null default now(),
  updated_at timestamptz not null default now()
);

create table if not exists public.app_data (
  tenant_id uuid not null references public.tenants(id) on delete cascade,
  entity text not null,
  record_id text not null,
  payload jsonb not null default '{}'::jsonb,
  created_at timestamptz not null default now(),
  updated_at timestamptz not null default now(),
  primary key (tenant_id, entity, record_id)
);

create index if not exists idx_memberships_tenant on public.memberships(tenant_id);
create index if not exists idx_app_data_tenant_entity on public.app_data(tenant_id, entity);
create index if not exists idx_subscriptions_status on public.subscriptions(status);
alter table public.subscriptions add column if not exists provider_payment_id text;
alter table public.subscriptions add column if not exists provider_payment_method_id text;
create index if not exists idx_subscriptions_provider_payment on public.subscriptions(provider_payment_id);

create or replace function public.is_tenant_member(target_tenant uuid)
returns boolean
language sql
security definer
set search_path = public
as $$
  select exists (
    select 1 from public.memberships
    where user_id = auth.uid() and tenant_id = target_tenant
  );
$$;

alter table public.tenants enable row level security;
alter table public.memberships enable row level security;
alter table public.subscriptions enable row level security;
alter table public.app_data enable row level security;

drop policy if exists "tenant members can read tenants" on public.tenants;
create policy "tenant members can read tenants" on public.tenants
for select using (public.is_tenant_member(id));

drop policy if exists "users can read own memberships" on public.memberships;
create policy "users can read own memberships" on public.memberships
for select using (user_id = auth.uid());

drop policy if exists "tenant members can read subscription" on public.subscriptions;
create policy "tenant members can read subscription" on public.subscriptions
for select using (public.is_tenant_member(tenant_id));

drop policy if exists "tenant members can read app data" on public.app_data;
create policy "tenant members can read app data" on public.app_data
for select using (public.is_tenant_member(tenant_id));

drop policy if exists "tenant members can insert app data" on public.app_data;
create policy "tenant members can insert app data" on public.app_data
for insert with check (public.is_tenant_member(tenant_id));

drop policy if exists "tenant members can update app data" on public.app_data;
create policy "tenant members can update app data" on public.app_data
for update using (public.is_tenant_member(tenant_id))
with check (public.is_tenant_member(tenant_id));

drop policy if exists "tenant members can delete app data" on public.app_data;
create policy "tenant members can delete app data" on public.app_data
for delete using (public.is_tenant_member(tenant_id));

create or replace function public.handle_new_user()
returns trigger
language plpgsql
security definer
set search_path = public
as $$
declare
  new_tenant uuid;
  store_name text;
begin
  store_name := coalesce(nullif(new.raw_user_meta_data->>'store_name',''), 'Новый магазин');
  insert into public.tenants(name, owner_user_id, slug)
  values (
    store_name,
    new.id,
    lower(regexp_replace(coalesce(store_name, 'store'), '[^a-zA-Z0-9а-яА-ЯёЁ]+', '-', 'g')) || '-' || substr(new.id::text, 1, 8)
  )
  returning id into new_tenant;
  insert into public.memberships(user_id, tenant_id, role) values (new.id, new_tenant, 'owner');
  insert into public.subscriptions(tenant_id, plan, status) values (new_tenant, 'trial', 'trialing');
  return new;
end;
$$;

drop trigger if exists on_auth_user_created on auth.users;
create trigger on_auth_user_created
after insert on auth.users
for each row execute procedure public.handle_new_user();

-- Team invitations and role administration.
create table if not exists public.invitations (
  id uuid primary key default gen_random_uuid(),
  tenant_id uuid not null references public.tenants(id) on delete cascade,
  email text not null,
  role text not null default 'manager',
  status text not null default 'pending',
  invited_by uuid not null references auth.users(id) on delete cascade,
  created_at timestamptz not null default now(),
  expires_at timestamptz not null default (now() + interval '7 days')
);

create index if not exists idx_invitations_tenant on public.invitations(tenant_id);
create index if not exists idx_invitations_email on public.invitations(lower(email));

create or replace function public.is_tenant_admin(target_tenant uuid)
returns boolean
language sql
security definer
set search_path = public
as $$
  select exists (
    select 1 from public.memberships
    where user_id = auth.uid()
      and tenant_id = target_tenant
      and role in ('owner','admin')
  );
$$;

alter table public.invitations enable row level security;

drop policy if exists "members can read team memberships" on public.memberships;
create policy "members can read team memberships" on public.memberships
for select using (public.is_tenant_member(tenant_id));

drop policy if exists "admins can read invitations" on public.invitations;
create policy "admins can read invitations" on public.invitations
for select using (public.is_tenant_admin(tenant_id));

drop policy if exists "admins can create invitations" on public.invitations;
create policy "admins can create invitations" on public.invitations
for insert with check (
  public.is_tenant_admin(tenant_id)
  and invited_by = auth.uid()
  and role in ('admin','manager','editor','viewer')
);

drop policy if exists "admins can cancel invitations" on public.invitations;
create policy "admins can cancel invitations" on public.invitations
for update using (public.is_tenant_admin(tenant_id))
with check (public.is_tenant_admin(tenant_id));

drop policy if exists "admins can delete invitations" on public.invitations;
create policy "admins can delete invitations" on public.invitations
for delete using (public.is_tenant_admin(tenant_id));



create table if not exists public.billing_checkout_sessions (
  id uuid primary key default gen_random_uuid(),
  tenant_id uuid not null references public.tenants(id) on delete cascade,
  provider text not null,
  provider_order_id text not null,
  provider_payment_id text,
  plan text not null,
  status text not null default 'created',
  created_at timestamptz not null default now(),
  updated_at timestamptz not null default now(),
  unique(provider, provider_order_id)
);
create index if not exists idx_billing_checkout_tenant on public.billing_checkout_sessions(tenant_id);
create index if not exists idx_billing_checkout_payment on public.billing_checkout_sessions(provider_payment_id);
alter table public.billing_checkout_sessions enable row level security;
create policy "tenant members can read own checkout sessions"
on public.billing_checkout_sessions for select
using (public.is_tenant_member(tenant_id));


-- Invitation acceptance by the invited account.
drop policy if exists "invitees can read own invitations" on public.invitations;
create policy "invitees can read own invitations" on public.invitations
for select using (lower(email) = lower(coalesce(auth.jwt()->>'email','')) and status = 'pending' and expires_at > now());

create or replace function public.accept_invitation(invite_id uuid)
returns uuid
language plpgsql
security definer
set search_path = public
as $$
declare
  inv public.invitations;
  uid uuid := auth.uid();
  user_email text := lower(coalesce(auth.jwt()->>'email',''));
begin
  if uid is null then raise exception 'AUTH_REQUIRED'; end if;
  select * into inv from public.invitations
  where id = invite_id and status = 'pending' and expires_at > now()
    and lower(email) = user_email
  for update;
  if not found then raise exception 'INVITATION_NOT_FOUND_OR_EXPIRED'; end if;
  insert into public.memberships(user_id, tenant_id, role)
  values(uid, inv.tenant_id, inv.role)
  on conflict (user_id, tenant_id) do update set role=excluded.role;
  update public.invitations set status='accepted' where id=invite_id;
  return inv.tenant_id;
end;
$$;


-- Owners/admins may update their tenant profile; ordinary members remain read-only.
drop policy if exists "tenant admins can update tenant" on public.tenants;
create policy "tenant admins can update tenant" on public.tenants
for update using (public.is_tenant_admin(id))
with check (public.is_tenant_admin(id));

-- Keep invitation roles constrained at database level.
alter table public.invitations drop constraint if exists invitations_role_check;
alter table public.invitations add constraint invitations_role_check
check (role in ('admin','manager','editor','viewer'));


-- Subscription renewal foundation (webhook/worker can use these fields later).
alter table public.subscriptions add column if not exists auto_renew boolean not null default false;
alter table public.subscriptions add column if not exists cancel_at_period_end boolean not null default false;
alter table public.subscriptions add column if not exists next_billing_at timestamptz;
alter table public.subscriptions add column if not exists provider_subscription_id text;
create index if not exists idx_subscriptions_next_billing on public.subscriptions(next_billing_at);
