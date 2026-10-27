-- Legacy YooKassa checkout rows created before expected amount/currency were
-- persisted cannot safely activate a subscription: the historical price cannot
-- be inferred from today's plan price. Retire unresolved rows without changing
-- already-confirmed checkouts or in-flight refund states.
--
-- A legacy confirmed checkout may still receive a provider-verified refund.
-- The webhook permits that revocation-only path when the expected amount is
-- absent; it never permits a legacy payment-success notification to activate
-- access.
update public.billing_checkout_sessions
   set status = 'deadline_expired',
       updated_at = now()
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
       'deadline_expired',
       'refund_pending',
       'refund_canceled',
       'partial_refunded',
       'partial_reversed'
   );
