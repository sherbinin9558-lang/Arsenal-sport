create table if not exists public.account_deletion_requests (
  id uuid primary key default gen_random_uuid(),
  user_id uuid not null references auth.users(id) on delete cascade,
  tenant_id uuid not null references public.tenants(id) on delete cascade,
  status text not null default 'requested' check (status in ('requested','approved','processing','completed','rejected','cancelled')),
  requested_at timestamptz not null default now(),
  processed_at timestamptz,
  note text
);

create index if not exists account_deletion_requests_user_idx
  on public.account_deletion_requests(user_id, requested_at desc);

alter table public.account_deletion_requests enable row level security;

drop policy if exists "account_deletion_requests_select_own" on public.account_deletion_requests;
create policy "account_deletion_requests_select_own"
on public.account_deletion_requests for select
to authenticated
using (user_id = auth.uid());

drop policy if exists "account_deletion_requests_insert_owner" on public.account_deletion_requests;
create policy "account_deletion_requests_insert_owner"
on public.account_deletion_requests for insert
to authenticated
with check (
  user_id = auth.uid()
  and exists (
    select 1 from public.memberships m
    where m.tenant_id = account_deletion_requests.tenant_id
      and m.user_id = auth.uid()
      and m.role = 'owner'
  )
);

revoke all on public.account_deletion_requests from anon;
grant select, insert on public.account_deletion_requests to authenticated;
