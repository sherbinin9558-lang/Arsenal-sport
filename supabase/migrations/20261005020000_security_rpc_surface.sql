-- Security hardening: keep SECURITY DEFINER logic out of the exposed public API schema.
-- Public functions remain thin SECURITY INVOKER wrappers for application/RLS compatibility.
-- Internal implementations live in the unexposed private schema.

create schema if not exists private;

create or replace function private.is_tenant_admin(target_tenant uuid)
returns boolean
language sql
security definer
set search_path = ''
as $function$
  select exists (
    select 1
    from public.memberships
    where user_id = auth.uid()
      and tenant_id = target_tenant
      and role in ('owner','admin')
  );
$function$;

create or replace function private.is_tenant_member(target_tenant uuid)
returns boolean
language sql
security definer
set search_path = ''
as $function$
  select exists (
    select 1
    from public.memberships
    where user_id = auth.uid()
      and tenant_id = target_tenant
  );
$function$;

create or replace function private.is_tenant_writer(target_tenant uuid)
returns boolean
language sql
security definer
set search_path = ''
as $function$
  select exists (
    select 1
    from public.memberships
    where user_id = auth.uid()
      and tenant_id = target_tenant
      and role in ('owner','admin','manager','editor')
  );
$function$;

create or replace function private.accept_invitation(invite_id uuid)
returns uuid
language plpgsql
security definer
set search_path = ''
as $function$
declare
  inv public.invitations;
  uid uuid := auth.uid();
  user_email text := lower(coalesce(auth.jwt()->>'email',''));
begin
  if uid is null then
    raise exception 'AUTH_REQUIRED';
  end if;

  select *
    into inv
    from public.invitations
   where id = invite_id
     and status = 'pending'
     and expires_at > now()
     and lower(email) = user_email
   for update;

  if not found then
    raise exception 'INVITATION_NOT_FOUND_OR_EXPIRED';
  end if;

  if exists (
    select 1
      from public.memberships
     where user_id = uid
       and tenant_id = inv.tenant_id
  ) then
    update public.invitations
       set status = 'accepted'
     where id = invite_id;
    return inv.tenant_id;
  end if;

  insert into public.memberships(user_id, tenant_id, role)
  values (uid, inv.tenant_id, inv.role);

  update public.invitations
     set status = 'accepted'
   where id = invite_id;

  return inv.tenant_id;
end;
$function$;

create or replace function private.set_member_role(
  target_tenant uuid,
  target_user uuid,
  new_role text
)
returns boolean
language plpgsql
security definer
set search_path = ''
as $function$
declare
  target_current_role text;
begin
  if not private.is_tenant_admin(target_tenant) then
    raise exception 'NOT_AUTHORIZED';
  end if;
  if new_role not in ('admin','manager','editor','viewer') then
    raise exception 'INVALID_ROLE';
  end if;
  if target_user = auth.uid() then
    raise exception 'CANNOT_CHANGE_OWN_ROLE';
  end if;

  select role into target_current_role
    from public.memberships
   where user_id = target_user
     and tenant_id = target_tenant
   for update;

  if not found then
    raise exception 'MEMBER_NOT_FOUND';
  end if;
  if target_current_role = 'owner' then
    raise exception 'CANNOT_CHANGE_OWNER_ROLE';
  end if;

  update public.memberships
     set role = new_role
   where user_id = target_user
     and tenant_id = target_tenant;

  return true;
end;
$function$;

revoke all on schema private from public;
grant usage on schema private to authenticated;

revoke execute on function private.is_tenant_admin(uuid) from public, anon;
revoke execute on function private.is_tenant_member(uuid) from public, anon;
revoke execute on function private.is_tenant_writer(uuid) from public, anon;
revoke execute on function private.accept_invitation(uuid) from public, anon;
revoke execute on function private.set_member_role(uuid,uuid,text) from public, anon;

grant execute on function private.is_tenant_admin(uuid) to authenticated;
grant execute on function private.is_tenant_member(uuid) to authenticated;
grant execute on function private.is_tenant_writer(uuid) to authenticated;
grant execute on function private.accept_invitation(uuid) to authenticated;
grant execute on function private.set_member_role(uuid,uuid,text) to authenticated;

create or replace function public.is_tenant_admin(target_tenant uuid)
returns boolean
language sql
security invoker
set search_path = ''
as $function$
  select private.is_tenant_admin(target_tenant);
$function$;

create or replace function public.is_tenant_member(target_tenant uuid)
returns boolean
language sql
security invoker
set search_path = ''
as $function$
  select private.is_tenant_member(target_tenant);
$function$;

create or replace function public.is_tenant_writer(target_tenant uuid)
returns boolean
language sql
security invoker
set search_path = ''
as $function$
  select private.is_tenant_writer(target_tenant);
$function$;

create or replace function public.accept_invitation(invite_id uuid)
returns uuid
language sql
security invoker
set search_path = ''
as $function$
  select private.accept_invitation(invite_id);
$function$;

create or replace function public.set_member_role(
  target_tenant uuid,
  target_user uuid,
  new_role text
)
returns boolean
language sql
security invoker
set search_path = ''
as $function$
  select private.set_member_role(target_tenant, target_user, new_role);
$function$;

revoke execute on function public.is_tenant_admin(uuid) from public, anon;
revoke execute on function public.is_tenant_member(uuid) from public, anon;
revoke execute on function public.is_tenant_writer(uuid) from public, anon;
revoke execute on function public.accept_invitation(uuid) from public, anon;
revoke execute on function public.set_member_role(uuid,uuid,text) from public, anon;

grant execute on function public.is_tenant_admin(uuid) to authenticated;
grant execute on function public.is_tenant_member(uuid) to authenticated;
grant execute on function public.is_tenant_writer(uuid) to authenticated;
grant execute on function public.accept_invitation(uuid) to authenticated;
grant execute on function public.set_member_role(uuid,uuid,text) to authenticated;

-- Main security follow-up: reduce browser-exposed RPC surface.
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
