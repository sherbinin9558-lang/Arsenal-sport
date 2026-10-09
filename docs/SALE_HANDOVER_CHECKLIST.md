# ShopPilot AI — pre-sale handover and billing readiness

Audit snapshot: 2026-10-09. This document is an audit checklist, not a certification that production has been fully tested.

## Confirmed from GitHub metadata

- PRs #118–#122 are open, target `main`, and are not merged.
- The latest reported GitHub Actions runs for each PR head commit show 9 completed workflows with conclusion `success`.
- This does not prove real payment-provider integration works; provider-dependent checks may be skipped when live credentials are absent.
- Production `main` was read for this audit. No production credentials were requested or used.

## PR review notes

- #118: replaces a test that manually assigned headers with a test invoking `SecurityHeadersMiddleware.dispatch`.
- #119: filters malformed WebMCP rows and tests allowlists/sensitive-field exclusion; this includes a small production-code hardening.
- #120: exercises request-size middleware for oversized and malformed Content-Length requests.
- #121: validates webhook JSON root type and returns HTTP 400 for non-object JSON. This change is not present in the currently inspected `main` version of `tbank_webhook.py`.
- #122: replaces source-text assertions with behavior-level tests for sanitized T-Bank/YooKassa webhook failures.

All five still require review against their exact diff and current base before merging. Re-run checks after any branch/base changes.

## Payment module findings from current `main`

- `billing.py` is a live YooKassa checkout integration, not a provider-independent sandbox. It calls the real YooKassa API when configured.
- `tbank_webhook.py` verifies provider payment state and applies subscription changes through the Supabase RPC `process_billing_payment_event`.
- Checkout persistence and webhook processing require server-side Supabase service-role credentials. These must remain server-only and must not be placed in browser code or repository files.
- The inspected payment modules do not expose an explicit, isolated fake-provider/sandbox mode. Do not test by supplying real provider credentials or creating real payments.
- `billing.py` currently sets `save_payment_method=True`; this should be explicitly reviewed and disabled unless recurring-payment authorization and provider requirements are intentionally implemented and documented.
- Error paths in `billing.py` can surface provider response text through raised exceptions. Ensure UI/logging boundaries do not display raw provider responses or secrets to end users.
- YooKassa/T-Bank callbacks and subscription state transitions need replay/idempotency, duplicate-event, out-of-order-event, failed-payment, refund, cancellation, and tenant-crossing tests.

## Required isolated test-mode design

1. Add an explicit server-side mode flag, defaulting to disabled for real payments. Do not infer test mode from missing credentials.
2. Introduce a fake payment-provider adapter that creates deterministic local checkout records and never calls external payment URLs.
3. Keep fake events on a separate test route or test harness; they must not be accepted as authenticated production-provider callbacks.
4. Exercise subscription transitions through the same domain/RPC contract where practical, against a disposable test database or isolated test doubles—not the production Supabase project.
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

- No confirmed isolated end-to-end fake payment mode.
- No live-provider verification (intentionally not run; no personal or real payment credentials used).
- No independent proof in this audit of production tenant-isolation behavior across every CRUD/admin path.
- No verified backup/restore and ownership-transfer rehearsal.
- No verified complete inventory of external accounts, deploy targets, domains, secrets, and third-party costs.
- PRs #118–#122 remain open and unmerged; their passing CI does not itself authorize merging.

## Release policy

Do not merge this branch or PRs #118–#122 automatically. Review diffs, run required tests, and merge only after explicit release approval. Do not represent the product as fully production-ready or payment-ready until the outstanding gates above have evidence.


## Follow-up audit findings — 2026-10-09

- PR #124 adds user-facing error sanitization for YooKassa/Supabase billing failures and regression tests. Its observed CI suite completed successfully, including the public login/browser smoke; it remains unmerged.
- PR #125 adds mocked tests for tenant-scoped writes and role restrictions. Its tenant-isolation workflow and other observed checks passed; it remains unmerged.
- PR #126 improves production smoke artifacts by capturing the app after Streamlit attaches its iframe and recording slow-start warnings. Its observed checks passed; it remains unmerged.
- PR #127 adds a test-only in-memory provider harness. The latest dedicated workflow passed 17 payment/webhook tests, and all observed workflows on its current head completed successfully. This is a test harness, not a production sandbox; it does not validate the real provider or the production Supabase RPC against a disposable database.
- PR #128 addresses a separate commercial gap: repository inspection found an `auto_renew` flag and UI, but no recurring-charge worker/scheduler in the repository tree. It stops requesting saved payment methods, blocks enabling auto-renewal in both SaaS and demo modes, and explains manual renewal. Its latest observed CI suite completed successfully, including the subscription safety tests and production browser smoke.
- PR #126's latest production browser run passed across five browser/viewport configurations. Time to visible login controls was approximately 5.0–7.2 seconds in that run, with no >10-second warning. A previous run had a 17.4-second first desktop load. These are small single-run smoke measurements, not a load test or a guarantee of consistently fast performance; PR #126 improves measurement visibility but does not itself make the app faster.
- `secrets.example.toml` now includes previously missing plan price, YooKassa webhook, T-Bank notification and receipt placeholders. It still contains no real credentials.

## Current release decision

Keep all open PRs unmerged until their latest CI completes and the diffs are reviewed together. Even after these PRs pass, the product is not yet certified as fully sale-ready: authenticated CRUD across all roles, production payment-provider verification, recurring billing (if marketed), and a real backup/restore and ownership-transfer rehearsal still require evidence.
