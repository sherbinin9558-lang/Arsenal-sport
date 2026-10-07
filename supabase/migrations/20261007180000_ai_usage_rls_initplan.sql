-- Optimize the authenticated-user predicate in the AI usage insert policy.
drop policy if exists "ai usage self insert" on public.ai_usage_events;
create policy "ai usage self insert"
on public.ai_usage_events
for insert to authenticated
with check (
  (select auth.uid()) = user_id
  and public.is_tenant_member(tenant_id)
);
