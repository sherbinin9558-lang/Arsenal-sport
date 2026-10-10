-- Only captured/final successful payment states may activate a subscription.
-- AUTHORIZED is an intermediate state for two-stage acquiring and is recorded only.
create or replace function public.process_billing_payment_event(
  p_provider text,
  p_event_key text,
  p_provider_payment_id text,
  p_status text,
  p_tenant_id uuid,
  p_plan text,
  p_provider_payment_method_id text default null,
  p_payload_hash text default null
)
returns jsonb
language plpgsql
security invoker
set search_path = public
as $process_billing_payment_event$
declare
  event_id uuid;
  event_status text;
  checkout public.billing_checkout_sessions;
  normalized_status text := lower(coalesce(p_status, ''));
  access_revoked boolean := false;
begin
  if p_provider not in ('tbank','yookassa') then
    raise exception 'INVALID_PROVIDER';
  end if;
  if btrim(coalesce(p_event_key,'')) = '' then
    raise exception 'EVENT_KEY_REQUIRED';
  end if;
  if btrim(coalesce(p_provider_payment_id,'')) = '' then
    raise exception 'PAYMENT_ID_REQUIRED';
  end if;
  if p_plan not in ('starter','pro','business') then
    raise exception 'INVALID_PLAN';
  end if;
  if p_tenant_id is null then
    raise exception 'TENANT_REQUIRED';
  end if;

  insert into public.billing_webhook_events(
    provider, event_key, provider_payment_id, status, payload_hash
  )
  values(
    p_provider, p_event_key, p_provider_payment_id, 'processing', p_payload_hash
  )
  on conflict (provider, event_key) do nothing
  returning id into event_id;

  if event_id is null then
    select id, status into event_id, event_status
      from public.billing_webhook_events
     where provider = p_provider and event_key = p_event_key
     for update;
    if event_status = 'processed' then
      return jsonb_build_object('ok', true, 'duplicate', true, 'status', 'processed');
    end if;
  end if;

  select * into checkout
    from public.billing_checkout_sessions
   where provider = p_provider
     and provider_payment_id = p_provider_payment_id
     and tenant_id = p_tenant_id
   for update;

  if not found then
    raise exception 'CHECKOUT_NOT_FOUND';
  end if;

  if checkout.plan <> p_plan then
    raise exception 'PLAN_MISMATCH';
  end if;

  -- AUTHORIZED is not a captured/settled payment; do not grant subscription access yet.
  if normalized_status in ('succeeded','confirmed') then
    perform public.activate_paid_subscription(
      p_tenant_id,
      p_plan,
      p_provider,
      p_provider_payment_id,
      p_provider_payment_method_id
    );
    update public.billing_checkout_sessions
       set status = 'confirmed', updated_at = now()
     where id = checkout.id;
  elsif normalized_status in ('refunded','reversed','canceled','cancelled','rejected','deadline_expired') then
    access_revoked := public.deactivate_paid_subscription(
      p_tenant_id,
      p_provider,
      p_provider_payment_id,
      normalized_status
    );
    update public.billing_checkout_sessions
       set status = normalized_status, updated_at = now()
     where id = checkout.id;
  elsif normalized_status in ('partial_refunded','partial_reversed') then
    update public.billing_checkout_sessions
       set status = normalized_status, updated_at = now()
     where id = checkout.id;
  else
    update public.billing_checkout_sessions
       set status = coalesce(nullif(normalized_status,''), 'unknown'), updated_at = now()
     where id = checkout.id;
  end if;

  update public.billing_webhook_events
     set status = 'processed',
         processed_at = now(),
         payload_hash = coalesce(p_payload_hash, payload_hash)
   where id = event_id;

  return jsonb_build_object(
    'ok', true,
    'duplicate', false,
    'status', normalized_status,
    'payment_id', p_provider_payment_id,
    'tenant_id', p_tenant_id,
    'plan', p_plan,
    'access_revoked', access_revoked
  );
end;
$process_billing_payment_event$;

revoke all on function public.process_billing_payment_event(
  text,text,text,text,uuid,text,text,text
) from public, anon, authenticated;
grant execute on function public.process_billing_payment_event(
  text,text,text,text,uuid,text,text,text
) to service_role;
