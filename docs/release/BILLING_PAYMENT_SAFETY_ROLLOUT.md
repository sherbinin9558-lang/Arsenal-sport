# Billing payment-safety rollout checklist

Status: **PREPARATION ONLY**. This document does not authorize applying migrations to production or enabling live payments.

## Backup and restore on the current Free project

The connected Supabase project is on the Free plan. Supabase documents that automated downloadable database backups are not available on Free; its recommended approach is a manual logical export with the Supabase CLI and an off-site copy. Source: https://supabase.com/docs/guides/platform/backups

Current read-only snapshot (2026-10-11): PostgreSQL 17.11, database approximately 15 MB, 9 public tables. RLS was enabled on all 9 public tables inspected. This is a size snapshot, not a verified backup.

Before release, an operator with database credentials must:
1. From Supabase Dashboard, open **Connect** and copy the database connection string. Prefer the session pooler if the machine/network is IPv4-only. Never paste the password or connection string into a GitHub issue, PR, chat, or logs.
2. Run Supabase CLI `db dump` in a trusted local environment with Docker available. Keep role, schema, and data dumps separate:
   ```sh
   supabase db dump --db-url "$DB_URL" -f roles.sql --role-only
   supabase db dump --db-url "$DB_URL" -f schema.sql
   supabase db dump --db-url "$DB_URL" -f data.sql --use-copy --data-only -x "storage.buckets_vectors" -x "storage.vector_indexes"
   ```
3. Store the three files encrypted, outside the application repository, and record checksums and the UTC creation time. Do not upload database dumps as ordinary GitHub Actions artifacts or commit them to Git.
4. Back up Storage objects separately: database dumps include Storage metadata but not the actual files. Also preserve application secrets/provider configuration separately using an approved secrets manager; never put secrets in the dump manifest.
5. Verify the files are non-empty and checksums match after copying. A successful dump alone is not proof of restorability.
6. Perform a restore rehearsal into a disposable local Supabase/Postgres environment, not Production. Validate schema, row counts for critical tables, RLS/policies, functions/triggers, auth-related objects, and Storage object recovery separately. Keep the rehearsal log with the backup manifest.
7. If no disposable restore target is available, mark restore verification **NOT DONE** and block the production billing migrations. Do not create a paid Supabase project/branch without explicit cost approval.

The Supabase CLI backup/restore guide is https://supabase.com/docs/guides/platform/migrating-within-supabase/backup-restore. Do not use a raw pg_dump as a drop-in replacement without reviewing Supabase-specific exclusions and restore compatibility.

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
