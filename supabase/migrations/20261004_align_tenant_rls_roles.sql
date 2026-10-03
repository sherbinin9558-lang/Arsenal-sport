-- Align tenant RLS policies with authenticated sessions.
drop policy if exists "tenant admins can update tenant" on public.tenants;
create policy "tenant admins can update tenant" on public.tenants
for update to authenticated
using ((select public.is_tenant_admin(id)))
with check ((select public.is_tenant_admin(id)));

drop policy if exists "tenant members can read tenants" on public.tenants;
create policy "tenant members can read tenants" on public.tenants
for select to authenticated
using ((select public.is_tenant_member(id)));
