-- Do not mutate legacy checkout rows until any still-payable provider payment
-- has been cancelled or reconciled. A local status update cannot cancel a
-- YooKassa payment link, and guessed historical prices must never be used.
--
-- Expose only a boolean reconciliation gate to the service; do not return
-- checkout identifiers or tenant data to readiness checks.
create or replace function public.has_unresolved_legacy_yookassa_checkouts()
returns boolean
language sql
stable
security invoker
set search_path = public
as $has_unresolved_legacy_yookassa_checkouts$
    select exists (
        select 1
          from public.billing_checkout_sessions
         where provider = 'yookassa'
           and (
               expected_amount is null
               or expected_amount::text in ('NaN', 'Infinity', '-Infinity')
               or expected_amount <= 0
               or expected_currency is null
               or regexp_replace(expected_currency, '[[:space:]]', '', 'g') = ''
           )
           and lower(coalesce(status, '')) not in (
               'confirmed',
               'refunded',
               'reversed',
               'canceled',
               'cancelled',
               'rejected',
               'refund_pending',
               'refund_canceled',
               'partial_refunded',
               'partial_reversed'
           )
    );
$has_unresolved_legacy_yookassa_checkouts$;

revoke all on function public.has_unresolved_legacy_yookassa_checkouts()
    from public, anon, authenticated;
grant execute on function public.has_unresolved_legacy_yookassa_checkouts()
    to service_role;

-- If unresolved rows exist, stop the migration transaction. First verify their
-- current state in the provider dashboard; cancel pending payments or perform
-- an approved refund/reconciliation for captured payments, then update the
-- corresponding rows through the project's controlled repair path.
do $legacy_yookassa_guard$
begin
    if public.has_unresolved_legacy_yookassa_checkouts() then
        raise exception using
            errcode = 'check_violation',
            message = 'LEGACY_YOOKASSA_CHECKOUTS_REQUIRE_PROVIDER_RECONCILIATION',
            detail = 'Unresolved YooKassa checkout(s) lack a valid expected amount/currency. Cancel or reconcile each provider payment before retrying this migration.';
    end if;
end
$legacy_yookassa_guard$;
