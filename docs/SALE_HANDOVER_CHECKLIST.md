# ShopPilot AI — pre-sale handover and billing readiness

Audit snapshot: 2026-10-09. This document is an audit checklist, not a certification that production has been fully tested.

## Confirmed from GitHub metadata

- The active release candidates are PRs #119, #121, #122, #123, #124, #125, #126, #127, #130, #132 and #133. None is merged. PRs #118 and #120 are closed as superseded; #128 and #129 are closed after their changes were consolidated into #124.
- All enabled checks have passed on #119, #121, #122, #123, #124, #125, #126 and #127. PR #130's dedicated error-sanitization, security, quality, RLS and production browser checks passed. PR #132's enabled checks passed. PR #133 addresses YooKassa callback/refund verification; its latest CI rerun is in progress after existing tests were updated to match the new contract.
- Optional public-app E2E, live-provider smoke, BrowserStack and production-secret checks are skipped because the required optional credentials/flags are not configured.
- This does not prove real payment-provider integration works; provider-dependent checks may be skipped when live credentials are absent.
- Production `main` was read for this audit. No production credentials were requested or used.

## PR review notes

- #119: filters malformed WebMCP rows and removes secret-like fields before data reaches WebMCP tools.
- #121: rejects non-object webhook JSON and tests actual security-header and request-size middleware behavior. This hardening remains outside `main` until a reviewed merge.
- #122: replaces source-text assertions with behavior-level tests for sanitized T-Bank/YooKassa webhook failures; it remains a separate open test candidate.
- #124: sanitizes billing-provider/storage errors, rejects invalid prices, disables payment-method saving, and blocks auto-renew until recurring charges exist.
- #125: adds tenant-scoped write/role tests. Its live Supabase RLS matrix passed with two tenants and five test users, including blocked cross-tenant reads and denied viewer/editor operations where expected.
- #126: improves production Playwright smoke diagnostics and captures the app after the Streamlit iframe appears.
- #127: adds a network-free fake-provider lifecycle test through the real webhook adapter. The Supabase RPC is simulated, so it does not prove database transaction/idempotency behavior.
- #130: sanitizes raw Supabase REST/Auth error bodies in `saas_core.py` and adds regression tests. This addresses an additional raw-error path found during the follow-up audit.
- #132: adds a forward-only migration so `AUTHORIZED` is not treated as a captured payment when activating subscriptions. CI passed; validate the exact T-Bank acquiring mode and run the transition against a disposable database before release.
- #133: allows standard YooKassa callbacks without a custom Bearer header while checking current payment/refund state directly with YooKassa. It verifies refund-to-payment binding and gives distinct refund IDs distinct idempotency keys. CI must pass on the latest head; no real provider callback was run.

Passing CI does not authorize an automatic merge. Recheck the exact candidate diff and all checks immediately before release.

## Payment module findings from current `main`

- `billing.py` is a live YooKassa checkout integration, not a provider-independent sandbox. It calls the real YooKassa API when configured.
- `tbank_webhook.py` verifies provider payment state and applies subscription changes through the Supabase RPC `process_billing_payment_event`.
- Checkout persistence and webhook processing require server-side Supabase service-role credentials. These must remain server-only and must not be placed in browser code or repository files.
- The inspected payment modules do not expose an explicit, isolated fake-provider/sandbox mode. Do not test by supplying real provider credentials or creating real payments.
- On `main`, `billing.py` still sets `save_payment_method=True` and billing exceptions can surface raw provider/storage response bodies. PR #124 fixes these on its candidate branch; `main` remains unchanged until merge.
- PR #127 exercises checkout, provider-state verification, webhook handling and duplicate event-key flow with fakes, but its Supabase RPC behavior is simulated. A disposable-database test is still needed for real transaction and idempotency semantics.
- Live YooKassa/T-Bank settlement/refund and production webhook verification remain intentionally untested because live payment credentials were not used.

## Required isolated test-mode design

1. Add an explicit server-side mode flag, defaulting to disabled for real payments. Do not infer test mode from missing credentials.
2. The test-only fake provider now exists in PR #127 and refuses unknown URLs; keep it test-only and do not add a production fake-payment bypass.
3. Keep fake events on a separate test route or test harness; they must not be accepted as authenticated production-provider callbacks.
4. Add a disposable Supabase integration run for the real `process_billing_payment_event` RPC; current fake lifecycle tests simulate the RPC response.
5. Test: create checkout; pending → succeeded; failed/cancelled; duplicate event; invalid signature; malformed JSON; unknown payment; refund; out-of-order event; tenant A cannot activate tenant B; internal errors are sanitized.
6. Keep all provider secrets and Supabase service-role keys in future-owner-managed deployment secrets. Use placeholders in templates and documentation only.
7. Before sale, provide a deployment inventory, environment-variable template, schema/migration inventory, backup/restore procedure, domain/hosting transfer steps, account ownership transfer plan, and post-transfer credential rotation checklist.

## Multi-tenant and operations acceptance gates

- Verify every data read/write is scoped to the authenticated user's selected tenant and server-side membership; never trust a tenant ID supplied only by the client.
- Verify owner/admin/member permissions for product, content plan, CRM/orders, warehouse, billing settings, and platform administration.
- Verify unauthorized cross-tenant reads and writes fail closed, including direct REST/RPC calls.
- Verify create/edit/delete, concurrent edit conflict behavior, persistence after reload/login, and error recovery for each core entity.
- Review database RLS policies, grants, security-definer functions, service-role usage, and migration reproducibility against a disposable test project.
- Run automated tests and browser acceptance on the release candidate. Capture commit SHA, workflow URLs, test results, and known limitations.

## Sale blockers — not yet proven closed by this repository review

- No live-provider verification (intentionally not run; no personal or real payment credentials used). This includes end-to-end YooKassa notification delivery and refund confirmation.
- The fake lifecycle harness does not validate the real billing RPC against a disposable database.
- The live RLS matrix passed for two tenants/five test users, but does not independently prove every authenticated CRUD/admin path in the whole application.
- No verified backup/restore and ownership-transfer rehearsal.
- No verified complete inventory of external accounts, deploy targets, domains, secrets, and third-party costs.
- PR #124 is the consolidated billing candidate; all enabled checks on its current head passed, while live-provider, BrowserStack, and optional public-app checks were skipped. PR #128 and #129 are closed as superseded by #124. PR #121 consolidates the middleware/input hardening and test improvements previously split across #118 and #120; those duplicate PRs are closed. PR #122 remains open as a separate webhook error-boundary test candidate.

## Release policy

Do not merge candidates automatically. PRs #119, #121, #122, #124, #125, #126 and #127 have passed their enabled CI checks; PR #130 and #132 have passed their enabled checks. PR #133 remains under CI validation after the latest test correction. Review final diffs and merge only after explicit release approval. Do not represent the product as fully production-ready or payment-ready until the outstanding gates above have evidence.


## Follow-up audit findings — 2026-10-09

- PR #124 initially added user-facing error sanitization for YooKassa/Supabase/T-Bank billing failures and regression tests. It now also includes the safety changes from #128: no saved payment methods and no misleading auto-renew toggle until recurring billing exists. All enabled checks on the combined head passed; optional public-app E2E, live provider smoke, BrowserStack, and production-secret checks were skipped.
- PR #125 adds mocked tests for tenant-scoped writes and role restrictions. Its tenant-isolation workflow and other observed checks passed; it remains unmerged.
- PR #126 improves production smoke artifacts by capturing the app after Streamlit attaches its iframe and recording slow-start warnings. Its observed checks passed; it remains unmerged.
- PR #127 adds a test-only in-memory provider harness. Its dedicated workflow and all enabled checks passed. This is a test harness, not a production sandbox; it does not validate the real provider or the production Supabase RPC against a disposable database.
- PR #128's changes have been copied into PR #124; the dedicated renewal-safety workflow and all other enabled checks passed on the combined head. PR #128 is now closed as superseded.
- PR #129 was closed as a duplicate after its unique T-Bank price/error-safety changes and tests were moved into PR #124. The latest #124 combined head includes the renewal safety changes from #128 as well, and all enabled CI jobs have passed.
- PR #126's latest production browser run passed across five browser/viewport configurations. Time to visible login controls was approximately 5.0–7.2 seconds in that run, with no >10-second warning. A previous run had a 17.4-second first desktop load. These are small single-run smoke measurements, not a load test or a guarantee of consistently fast performance; PR #126 improves measurement visibility but does not itself make the app faster.
- `secrets.example.toml` now includes previously missing plan price, YooKassa webhook, T-Bank notification and receipt placeholders. It still contains no real credentials.

## Follow-up audit — Supabase error boundaries

- PR #130 sanitizes Supabase REST error bodies in both the generic request helper and the paged reader. Its dedicated regression workflow passed. A broad QA run initially caught an existing test that expected the raw word `Forbidden`; that test was updated to assert the safe public contract. The latest broad QA and production browser checks must pass on the final head before acceptance.

## Current release decision

Keep all candidates unmerged until final checks and diff review. The live RLS matrix passed for two tenants/five test users; browser smoke passed on the completed candidates. Optional provider/BrowserStack/public-E2E checks remain skipped. The product is not yet certified as fully sale-ready: real provider settlement/refund, disposable-database billing RPC validation, complete authenticated CRUD/admin coverage, and backup/restore plus ownership-transfer rehearsal still require evidence.


## Payment follow-up — 2026-10-09 (latest candidate checks)

- PR #133 (`fix/yookassa-webhook-verification`) has passing enabled checks on head `1235243ff7d7d4cec7753e37951aa80dae2b1fa2`, including the production Playwright browser smoke. BrowserStack was skipped. This confirms the automated browser smoke and mocked/contract coverage, not real payment settlement, provider callback delivery, or real refunds.
- PR #134 (`feat/sbp-qr-checkout`) adds an explicit YooKassa SBP checkout path and disables payment-method saving. Its unit/contract workflow passed; optional public-app E2E was skipped because the optional URL/flag is not configured. Merchant-side SBP enablement and test-mode payment verification remain open.
- PR #135 (`fix/billing-provider-error-sanitization`) sanitizes provider/database error responses and adds a regression test. Branch-quality and QA automation checks passed; optional public-app E2E was skipped.
- PR #134 is stacked on #133; PR #135 is stacked on #134. Review the chain in dependency order. Do not merge a child before its base has been accepted and revalidated.
- None of these changes is merged into `main`; the production deployment remains unchanged. The latest `main` SHA recorded for this audit is `2fb836a34d7b0b18bc333dc4e282276559f582d4`.
- Remaining hard sale gates: real provider test-mode payment/refund/callback verification; real `process_billing_payment_event` RPC test against a disposable Supabase database; backup-and-restore rehearsal; full authenticated CRUD/tenant-authorization matrix; load/performance validation; ownership-transfer and secret-rotation rehearsal. These require isolated test infrastructure or buyer-owned credentials and must not be simulated as completed.


## Audit delta — 2026-10-09 18:30 UTC

Latest GitHub metadata check (exact candidate heads):

- PR #131 head `34dec9fcf4cc5a6ac09da1b460cbb062500958f5`: Unit and contract tests passed; optional public-app E2E skipped. The PR remains open and targets `audit/pre-sale-billing-readiness`.
- PR #133 head `1235243ff7d7d4cec7753e37951aa80dae2b1fa2`: Unit/contract tests, Python quality, syntax, regression, webhook contract, dependency audit, security/SAST/dependency checks, RLS integration, commercial gate, observability, and Production browser matrix passed in the observed run. Optional public-app E2E, provider smoke, BrowserStack, production-secret, and browser-WebMCP checks were skipped. The latest run's unit/contract tests also passed. No real YooKassa payment, notification delivery, or refund was performed.
- PR #134 head `55fc2518a39c1b404a7f426288a6286370ab9786`: Python quality passed. One unit/contract run was cancelled; an earlier run on the same head passed. Optional public-app E2E was skipped. PR #135 is stacked on this head and its tests passed, but this does not replace rechecking #134's own current required checks before any merge.
- PR #135 head `e9fd44659b281bea155979c5b49ed94b856d6db9`: Unit/contract tests and Python quality passed; optional public-app E2E skipped.
- PR #131 is documentation-only; its latest unit/contract check passed. These statuses describe GitHub Actions results, not live provider/database acceptance.
- Dependency order remains #133 → #134 → #135. All three remain open and unmerged. Do not merge them automatically.

Outstanding acceptance gates remain: real YooKassa test-account checkout/callback/refund; execution of `process_billing_payment_event` against a disposable PostgreSQL/Supabase database; broader tenant CRUD/role tests; backup/restore rehearsal; performance/load testing; and complete owner-transfer/infrastructure inventory. Do not add personal bank details or production payment secrets to the repository.


### Cross-PR dependency warning

PR #124 is a separate open candidate based on `main` at `f8c4328c1b3a2e7563fb8b5ec89560b9f6b811c5`. It contains additional safeguards not present in the current #133 → #134 → #135 stack, including finite/positive tariff-price validation and T-Bank/other billing error handling and auto-renew safety. The stack currently targets #133 on `main`, #134 on #133, and #135 on #134; none includes PR #124 merely because it exists separately.

Before release, reconcile the overlap explicitly: preserve the #124 safeguards while integrating #133–#135, then rerun CI on the final release-candidate heads. Do not assume merging #133–#135 alone delivers all protections described in #124. Main currently still has `save_payment_method=True`, permits non-finite float tariff values through `plan_price`, and can include raw YooKassa/Supabase response text in billing exceptions. These issues are not fixed in Production by the open PRs.
