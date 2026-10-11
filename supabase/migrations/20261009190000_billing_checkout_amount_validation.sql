-- Record the exact server-created checkout amount and currency.
-- Existing rows remain nullable for compatibility; paid activation will fail closed until
-- a new checkout has these values and the authoritative provider amount matches.
alter table public.billing_checkout_sessions
  add column if not exists expected_amount numeric(12,2),
  add column if not exists expected_currency text;

comment on column public.billing_checkout_sessions.expected_amount is
  'Expected amount from the server-created checkout; used to validate provider settlement.';
comment on column public.billing_checkout_sessions.expected_currency is
  'Expected ISO currency from the server-created checkout.';
