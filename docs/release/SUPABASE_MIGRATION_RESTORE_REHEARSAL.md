# Supabase migration and recovery rehearsal

Status: **procedure prepared; rehearsal not executed**. This document deliberately does not authorize changes to Production.

## Non-negotiable safety rules

- Never point a rehearsal at the Production Supabase project.
- Do not place database URLs, passwords, service-role keys, access tokens, or backup files in Git.
- Use a separate disposable Supabase project with synthetic data and its own credentials.
- Do not run `supabase db push`, `supabase migration repair`, restore, or destructive SQL until the target project reference has been independently verified.
- Keep payment provider credentials absent. No live or real-money payment is part of this rehearsal.

## Gate 0 — identify the target

1. Create or select a dedicated disposable Supabase project; label it clearly as a test environment.
2. Record its project reference in the operator's private notes, not in this repository.
3. Confirm the dashboard URL and project reference match the test project. Have a second person verify if available.
4. Confirm no Production project secrets are selected in GitHub Actions. Prefer running locally with test-only credentials or a dedicated GitHub Environment named `supabase-rehearsal`.
5. If any target identity is ambiguous, stop.

## Gate 1 — inventory migrations

1. Check out the exact PR dependency chain and record the commit SHA for each branch.
2. List migration filenames in lexical order and compare them with the test database's migration history.
3. Specifically reconcile `20261009193000_prevent_reactivation_after_refund.sql`: it exists byte-for-byte identically in the #174 and #178 lines of work. It must be applied once, not duplicated or silently renamed.
4. Verify prerequisite billing migrations are present in order:
   - `20261009170000_require_captured_payment_for_activation.sql`
   - `20261009190000_billing_checkout_amount_validation.sql`
   - `20261009193000_prevent_reactivation_after_refund.sql`
5. Inspect each SQL diff and confirm no unexpected destructive operations, broad grants, or production-specific assumptions.

## Gate 2 — disposable database migration rehearsal

1. Take a baseline export of the disposable database and retain it outside the repository.
2. Record the initial migration history and relevant schema for billing checkout sessions and `process_billing_payment_event`.
3. Apply the proposed migration set to the disposable project only.
4. Save command output and migration history. Any failed migration means stop; do not mark it repaired merely to make the sequence pass.
5. Re-run the same migration process from a clean disposable project to check reproducibility.
6. Confirm the expected checkout amount/currency columns exist and the RPC only activates entitlement on captured/succeeded/confirmed states as intended by the final migration.
7. Confirm late events cannot reactivate a refunded, reversed, canceled, rejected, or expired checkout. Exercise idempotency and mismatched tenant/payment identity cases using synthetic fixtures.
8. Verify execute permissions are restricted as intended; anonymous/authenticated roles must not gain access to service-only billing functions.

## Gate 3 — backup and restore rehearsal

1. Create a fresh backup/export of the disposable project using the supported Supabase/Postgres tooling available to that project.
2. Record timestamp, tool/version, exit code, file size, and checksum. Store the artifact encrypted and outside Git.
3. Restore into a second disposable project or a newly reset isolated test database, never over Production.
4. Record the restore command output and exit code.
5. Compare schema/migration history and row counts for selected synthetic tables before and after restore.
6. Run smoke checks: login-independent DB connectivity, tenant isolation/RLS tests, billing state-machine tests, and application unit/contract tests.
7. A backup is not proven recoverable until the restore and verification checks pass.

## Gate 4 — payment-provider boundary

- Do not test live charges.
- If a YooKassa test account becomes available, use test credentials and synthetic orders only.
- Verify signature/notification validation, amount and currency matching, provider payment identity, idempotency, captured-vs-authorized handling, and refund/late-event terminal states.
- Without a provider test account, mark provider end-to-end verification **BLOCKED**, not passed.

## Evidence required before release

- [ ] Test project identity independently verified; no Production target used.
- [ ] Exact branch/commit SHAs recorded.
- [ ] Migration inventory and duplicate migration reconciliation recorded.
- [ ] Clean migration rehearsal passes twice.
- [ ] Billing state-machine and tenant-isolation checks pass.
- [ ] Backup artifact checksum recorded outside Git.
- [ ] Restore to a separate disposable target succeeds.
- [ ] Post-restore checks pass.
- [ ] YooKassa test-mode payment/refund evidence attached, or provider gate explicitly remains blocked.
- [ ] CI is green on the exact final PR heads.
- [ ] Human review and repository merge rules are satisfied.

## Current known blockers

- No verified disposable Supabase target is established in this procedure.
- No successful restore rehearsal evidence is recorded here.
- YooKassa test-mode payment/refund has not been verified.
- Do not merge/deploy the payment chain until these blockers are resolved or explicitly accepted by the release owner with documented risk.
