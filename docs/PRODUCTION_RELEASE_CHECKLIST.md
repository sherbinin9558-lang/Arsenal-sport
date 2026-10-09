# Production Release Checklist — AI Content Manager

This checklist separates repository/CI evidence from live production evidence. A green workflow is not proof that external payment providers, production database migrations, or real-device rendering have been verified.

## Current release blockers

- [ ] **Billing schema migration:** verify that the production Supabase database contains `billing_checkout_sessions.expected_amount` and `expected_currency`. The current audit found these columns missing. Do not enable amount-validated checkout until the matching migration is reviewed, applied by an authorized operator, and verified.
- [ ] **Payment provider sandbox:** run end-to-end test-mode checkout and webhook tests for each enabled provider (including success, amount/currency mismatch, duplicate webhook, refund/cancel, and delayed/out-of-order notification). Do not use real charges for acceptance.
- [ ] **Captured-payment invariant:** verify against the actual deployed database function that `AUTHORIZED` alone cannot activate a paid subscription; only a confirmed/captured successful payment can.
- [ ] **Supabase Auth security:** enable compromised-password protection in the Supabase Auth settings, then rerun the Security Advisor and record the result.
- [ ] **Tenant isolation:** verify cross-tenant reads and writes are denied using separate test tenants and non-admin users; retain test output.
- [ ] **Production browser acceptance:** run the production smoke/Playwright suite and inspect the actual application response, not only the hosting platform's status/maintenance page.
- [ ] **Real-device layout:** visually verify login, main dashboard, settings, billing, dialogs, and navigation in iPhone Safari and Android Chrome. Automated browser tests do not replace this check.
- [ ] **Buyer handoff:** remove owner-specific secrets and test credentials from handoff materials; document environment variables, migrations, provider setup, deployment, backup/restore, and support boundaries.

## Safe execution order

1. Review the exact migration and billing-function definitions in version control.
2. Run isolated CI SQL integration and automated QA on the candidate branch.
3. Apply migrations only after explicit release authorization and a verified backup/rollback plan.
4. Configure provider sandbox credentials and run provider-specific end-to-end tests.
5. Re-run database security checks, tenant-isolation tests, and production browser acceptance.
6. Record evidence for each item above. Leave the release blocked while any payment/security/tenant-isolation item is unchecked.

## Release decision

**Not yet certified for commercial production or sale as a verified, fully operational SaaS.** Repository checks can pass while live production prerequisites remain incomplete. Keep changes on review branches until the dependent pull requests and release evidence are reviewed. Do not put personal payment or banking credentials into a pre-sale build; the eventual buyer should configure their own provider account.

## Evidence to attach during final acceptance

- Commit SHA and links to successful CI runs.
- Production schema verification query output (column names only; never include secrets).
- Payment-provider sandbox event IDs and sanitized results.
- Security Advisor results after remediation.
- Tenant-isolation test results.
- Production browser test result and real-device screenshots.
