-- Defense-in-depth: no anonymous table privileges in the public SaaS schema.
-- RLS remains the primary access control mechanism for application tables.
revoke all on table public.tenants from anon;
revoke all on table public.subscriptions from anon;
revoke all on table public.billing_checkout_sessions from anon;
