-- Do not mutate legacy checkout rows until any still-payable provider payment
-- has been cancelled or reconciled. A local status update cannot cancel a
-- YooKassa payment link, and guessed historical prices must never be used.
--
-- If unresolved legacy rows exist, stop the migration. First verify their
-- current state in the provider dashboard; cancel pending payments or perform
-- an approved refund/reconciliation for already-captured payments, then update
-- the corresponding database rows through the project's controlled repair path.
-- This guard is read-only and intentionally does not change checkout statuses.
do $legacy_yookassa_guard$
declare
    unresolved_count bigint;
begin
    select count(*)
      into unresolved_count
      from public.billing_checkout_sessions
     where provider = 'yookassa'
       and (
           expected_amount is null
           or expected_currency is null
           or btrim(expected_currency) = ''
           or expected_amount <= 0
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
       );

    if unresolved_count > 0 then
        raise exception using
            errcode = 'check_violation',
            message = 'LEGACY_YOOKASSA_CHECKOUTS_REQUIRE_PROVIDER_RECONCILIATION',
            detail = format(
                'Found %s unresolved YooKassa checkout(s) without a valid expected amount/currency. Cancel or reconcile each provider payment before retrying this migration.',
                unresolved_count
            );
    end if;
end
$legacy_yookassa_guard$;
