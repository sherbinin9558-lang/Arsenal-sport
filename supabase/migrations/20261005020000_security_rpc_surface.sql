-- Reduce the exposed RPC surface for tenant security helpers.
-- These helpers are used by RLS / privileged database functions, not by the browser.
-- Keep invitation and role-management RPCs executable by authenticated users.
revoke execute on function public.is_tenant_admin(uuid) from authenticated;
revoke execute on function public.is_tenant_member(uuid) from authenticated;
revoke execute on function public.is_tenant_writer(uuid) from authenticated;

-- billing_webhook_events is service-role only. Keep RLS explicit and deny signed-in clients.
drop policy if exists "billing webhook events deny authenticated" on public.billing_webhook_events;
create policy "billing webhook events deny authenticated"
on public.billing_webhook_events
for all to authenticated
using (false)
with check (false);
