create index if not exists account_deletion_requests_tenant_idx
  on public.account_deletion_requests(tenant_id);

drop policy if exists "account_deletion_requests_select_own" on public.account_deletion_requests;
create policy "account_deletion_requests_select_own"
on public.account_deletion_requests for select
to authenticated
using (user_id = (select auth.uid()));

drop policy if exists "account_deletion_requests_insert_owner" on public.account_deletion_requests;
create policy "account_deletion_requests_insert_owner"
on public.account_deletion_requests for insert
to authenticated
with check (
  user_id = (select auth.uid())
  and exists (
    select 1 from public.memberships m
    where m.tenant_id = account_deletion_requests.tenant_id
      and m.user_id = (select auth.uid())
      and m.role = 'owner'
  )
);
