-- Persist the exact expected checkout amount so provider callbacks cannot activate
-- a plan using a payment for a different amount or currency.
alter table public.billing_checkout_sessions
  add column if not exists expected_amount numeric(12,2),
  add column if not exists expected_currency text;

comment on column public.billing_checkout_sessions.expected_amount is
  'Expected amount from the server-created checkout; used to validate provider settlement.';
comment on column public.billing_checkout_sessions.expected_currency is
  'Expected ISO currency from the server-created checkout.';
