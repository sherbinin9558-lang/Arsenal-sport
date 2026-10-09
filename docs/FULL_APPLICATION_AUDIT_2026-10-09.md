# Full application audit — 2026-10-09

Scope: static review of the default branch at `2fb836a34d7b0b18bc333dc4e282276559f582d4`, test inventory, database migrations, billing/webhook code, tenant data access, automation/MAX and responsive UI. This is a code review, not a claim that every runtime path or production database was exercised.

## Executive result

**Not yet safe to label production-ready for resale.** The repository has broad test coverage and hardening migrations, but several acceptance gates are still open. Do not deploy stacked billing changes until their migration order and CI are verified.

## Findings

### P0 — Payment activation accepts authorization-only state in the default branch
Evidence: `supabase/migrations/20261006090000_billing_refund_lifecycle.sql` defines `process_billing_payment_event` with `normalized_status in ('succeeded','confirmed','authorized')`, which calls `activate_paid_subscription`. An authorization-only payment must not be treated as captured/settled. PR #132/#136 contain forward migration work, but are not part of the audited default-branch SHA.
- Required fix: apply a forward-only migration after all billing lifecycle migrations; only final provider success states activate access.
- Acceptance: SQL contract tests and disposable-database RPC tests prove `authorized` never activates, `succeeded/confirmed` activates once, and duplicates are idempotent.

### P0 — Default branch does not bind successful checkout to expected amount/currency
Evidence: default `billing.py` saves provider order/payment IDs, tenant and plan but no expected amount/currency. The webhook resolves the checkout and provider status, but amount/currency validation is not present in the reviewed main-branch path.
- Required fix: save server-calculated amount/currency at checkout creation and compare with provider-authoritative payment before activation. Reject missing/mismatched values. Handle old rows with an explicit migration/reconciliation plan.
- Acceptance: mismatch tests prove the subscription transition RPC is not called.

### P1 — Missing selected tenant silently falls back to `demo-tenant`
Evidence: default `saas_core.py` implements `tenant_id()` with a `demo-tenant` default even when SaaS mode is enabled. Main authorization/RLS still limits what a user can access, but silent fallback is unsafe and can obscure initialization errors or cause writes to target an unintended tenant identifier.
- Proposed fix in this audit branch: return an empty tenant ID when SaaS is enabled but no tenant has been selected; preserve demo tenant only for explicit demo mode. Add regression coverage.
- Acceptance: auth/bootstrap, onboarding, tenant selector, data reads/writes and admin flows pass with both missing and selected tenant states.

### P1 — Mobile MAX dialog CSS overrides Streamlit's own layout
Evidence: default `app.py` forced `div[data-testid="stDialog"]` to `position:fixed; inset:0`, applied an extreme z-index, and forced all descendants visible. This matches the screenshot symptoms (oversized white dialog, low contrast, controls pushed down).
- Proposed fix is isolated in PR #137. Unit/contract tests passed for its current head; optional public-app E2E was skipped. iPhone Safari visual confirmation remains outstanding.

### P1 — Global CSS overrode selected theme and mobile layout
Evidence: a later unconditional `.stApp{background:#f6f7fb}` and white sidebar background overrode earlier dark-mode CSS. The mobile dialog override forced the dialog wrapper to `position:fixed; inset:0` with an extreme z-index, and the light-theme select controls had dark surfaces with dark text.
- Fix proposed in PR #138: theme-aware CSS variables for app/sidebar/toolbar, explicit light select contrast, neutral toolbar colors, and viewport-bounded MAX dialog.
- Regression tests cover CSS invariants. BrowserStack/live public E2E jobs are skipped in current CI; visual iPhone confirmation remains necessary.

### P1 — Billing changes are stacked and not deployed
PRs #133–#136 are dependent. Reviewing a child branch alone is not sufficient: each base must be merged in order and the final combined head must pass the full suite. Real provider test-mode payment, notification delivery, refund, and SBP merchant enablement have not been verified.

### P1 — Production tenant/RLS behavior has not been demonstrated end-to-end in this audit
The repository contains RLS and tenant-isolation tests, but mocked request tests do not establish the deployed Supabase grants/policies/RPC permissions or prove cross-tenant denial against the current production schema.
- Required acceptance: run the RLS integration suite against a disposable Supabase project; verify user A cannot read/write tenant B; verify service-role-only billing RPC grants; export/restore a test tenant.

### P2 — Large modules raise regression risk
`app.py` and `saas_core.py` are large, cross-cutting modules. This is not by itself a defect, but increases review and change risk. Refactor incrementally only after behavior is covered by tests; avoid a rewrite during payment and production hardening.

## Required release gates

- [ ] All PRs merged in dependency order only after review; no direct edits to `main`.
- [ ] Full CI green on the final combined commit; no cancelled required checks.
- [ ] Disposable-database migration run from an empty schema and from the latest supported schema.
- [ ] RLS cross-tenant integration tests pass.
- [ ] YooKassa test-mode payment, captured status, callback retry, refund and duplicate callback verified.
- [ ] SBP checkout verified on a merchant account with SBP enabled.
- [ ] Browser matrix covers mobile/tablet/desktop; visual iPhone Safari check completed.
- [ ] Backup/export/restore and account deletion rehearsed.
- [ ] Buyer handover lists required secrets, service ownership, migration order, known limits, and provider setup without seller personal credentials.

## Changes started by this audit

- Branch `audit/full-app-hardening`: fail-closed tenant ID when SaaS mode has no selected tenant, plus a regression test.
- PR #137: separate mobile dialog fix.
- PR #136: separate checkout amount/currency and final-payment-state fix, stacked on billing PRs.

No production database migration was run. No live payment was made. No change was merged to `main`.
