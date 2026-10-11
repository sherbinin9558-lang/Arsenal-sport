# Billing payment-safety rollout checklist

Status: **PREPARATION ONLY**. This document does not authorize applying migrations to production or enabling live payments.

## Required migration order

Apply in timestamp order, and only after a verified backup and a tested restore path:

1. `supabase/migrations/20261009170000_require_captured_payment_for_activation.sql`
   - Stops activation on intermediate `AUTHORIZED` status.
2. `supabase/migrations/20261009190000_billing_checkout_amount_validation.sql`
   - Adds nullable `expected_amount` and `expected_currency` columns.
3. `supabase/migrations/20261009193000_prevent_reactivation_after_refund.sql`
   - Prevents a delayed success event from reactivating a terminal checkout.

Do not apply only the SQL migrations while leaving the webhook application on code that does not populate or verify expected amount/currency. Deploy code and schema as a coordinated release.

## Preflight gates

- Confirm the exact target Supabase project ID and that a recent backup is restorable.
- Confirm the three migration files are present in the exact release commit.
- Confirm the current production migration history and function definition immediately before rollout.
- Confirm checkout creation persists server-calculated amount and currency for both providers.
- Confirm T-Bank and YooKassa credentials are configured in the billing-webhook runtime; do not print or copy secret values.
- Run CI for the exact release SHA. Required checks: payment lifecycle, QA unit/contract tests, Python syntax, security hardening, RLS audit, branch quality, production browser acceptance.
- Provider smoke tests require explicit test credentials and test-mode payments. Never use a real customer or production charge as a smoke test.
- Ensure an operator can pause checkout/webhook traffic and revert the application version without deleting payment records.

## Database verification after migration

Read-only checks must confirm:
- `billing_checkout_sessions.expected_amount` and `expected_currency` exist.
- `process_billing_payment_event` activates only on `succeeded` or `confirmed`, never `authorized`.
- EXECUTE on `process_billing_payment_event` remains restricted to `service_role`.
- The new terminal-checkout guard is present.
- RLS remains enabled and tenant access policies are unchanged.

## Test matrix before accepting payments

- Missing expected amount/currency: fail closed, no subscription activation.
- Provider amount or currency mismatch: fail closed, no subscription activation.
- T-Bank `AUTHORIZED`: no activation.
- Verified settled payment: exactly one activation, including duplicate webhook delivery.
- Partial refund: subscription is not deactivated as though fully refunded.
- Full refund: access is revoked according to the established subscription policy.
- Delayed success after full refund/cancellation: ignored; no reactivation.
- Browser return URL alone: never activates a subscription.
- Wrong tenant, plan, provider payment ID, or unknown checkout: rejected.
- Provider API unavailable or invalid credentials: fail closed and produce sanitized logs.

## Release and rollback

1. Take and verify a backup/restore point.
2. Run migrations in order against staging and execute the full matrix.
3. Confirm the deployed app commit and migration state match.
4. Apply migrations to production in order only during an approved release window.
5. Deploy the matching application version and verify health/readiness without creating a real charge.
6. Run read-only schema/function checks and provider test-mode smoke checks where supported.
7. If checks fail, disable new checkout initiation and roll back application code. Do not blindly roll back schema or delete payment events; use a reviewed forward-fix or tested database restore plan.
8. Keep live payments disabled until end-to-end provider verification succeeds.

## Current known blocker

At the last read-only inspection of Supabase project `lmdiwzkuvictysmdtuld`, the two expected amount/currency columns were absent and the migration history ended at `20261007182130`. This must be rechecked immediately before any release. No production migration was run as part of this preparation.
