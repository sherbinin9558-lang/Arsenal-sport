-- Persistent AI usage metering for commercial SaaS economics.
-- Every event is tenant/user scoped and readable only by members of that tenant.

create table if not exists public.ai_usage_events (
  id uuid primary key default gen_random_uuid(),
  tenant_id uuid not null references public.tenants(id) on delete cascade,
  user_id uuid not null references auth.users(id) on delete cascade,
  operation text not null,
  provider text not null default 'local',
  model text not null default 'deterministic',
  input_tokens integer not null default 0 check (input_tokens >= 0),
  output_tokens integer not null default 0 check (output_tokens >= 0),
  request_count integer not null default 1 check (request_count > 0),
  estimated_cost_rub numeric(14,6) not null default 0 check (estimated_cost_rub >= 0),
  metadata jsonb not null default '{}'::jsonb,
  created_at timestamptz not null default now()
);

create index if not exists idx_ai_usage_tenant_created
  on public.ai_usage_events (tenant_id, created_at desc);

create index if not exists idx_ai_usage_user_created
  on public.ai_usage_events (user_id, created_at desc);

alter table public.ai_usage_events enable row level security;

drop policy if exists "ai usage tenant member select" on public.ai_usage_events;
create policy "ai usage tenant member select"
on public.ai_usage_events
for select to authenticated
using (
  public.is_tenant_member(tenant_id)
);

drop policy if exists "ai usage self insert" on public.ai_usage_events;
create policy "ai usage self insert"
on public.ai_usage_events
for insert to authenticated
with check (
  auth.uid() = user_id
  and public.is_tenant_member(tenant_id)
);

revoke all on public.ai_usage_events from anon;
grant select, insert on public.ai_usage_events to authenticated;
