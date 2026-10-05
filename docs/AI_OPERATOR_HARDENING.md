# ShopPilot AI — hardening branch

This branch is intentionally isolated from `main`.

## Scope
- MAX as a safe AI-operator command center.
- Explicit confirmation for write actions.
- Action audit trail in the current MAX session.
- Business snapshot and measurable operational signals.
- Regression tests for operator intent/permission boundaries.
- GitHub Actions quality gate.
- Existing tenant isolation, roles, optimistic concurrency and WebMCP remain untouched by this branch.

## Commercial-readiness checklist
1. Reliability: run all existing application checks and the branch quality gate.
2. MAX: connect each supported action to a real business operation; writes require confirmation.
3. Simplicity: keep MAX as the primary task entry point.
4. Business value: expose orders, revenue, leads, conversion, low-stock and content workload.
5. Safety: never allow a write action to execute without explicit approval.
6. Tenant isolation: every data operation must continue to be scoped by tenant.
7. Automation: prefer idempotent operations and avoid duplicate content-plan rows.
8. Integrations: verify each connected channel separately before production use.
9. CRM/sales: verify create/update/delete and concurrent writes.
10. Content: verify add/edit/delete and concurrent edits.
11. Analytics: show recommendations with clear "signal vs proven result" language.
12. Onboarding: first useful result should be achievable within one short session.
13. WebMCP: verify registration and execution on the deployed test branch before merge.
14. Roles: verify least-privilege behavior for every write action.
15. Auditability: retain action status and failure reasons.
16. UX/mobile: verify the MAX dialog and controls on phone and tablet.
17. Speed: avoid redundant remote reads and stale snapshots.
18. Monetization: keep billing isolated until payment integration is intentionally enabled.
19. Positioning: sell the product as an AI operator, not as a list of modules.
20. Evidence: collect real-user time saved, actions completed and business outcomes.

## Verification status
- Static branch inspection: completed.
- Main isolation check: completed; branch remains ahead of main and has no main-side changes.
- Automated GitHub workflow execution: not yet confirmed by the available workflow-run query.
- Live deployed-branch/WebMCP smoke: not yet confirmed.
- Payment integration: intentionally out of scope.

## Merge rule
No changes from this branch should be merged to `main` until the complete regression checklist is green and the deployed branch is manually verified.


## Final integration verification — 2026-10-05

- Integration branch: `integration/final-20261005`.
- Combined from `ai-operator-hardening-20261005` plus the latest UX/auth work from the separate project branch set: owner guide/mobile MAX cleanup and request-cookie auth restore.
- GitHub Actions final head: `433a3e3bffb863d01187bd5abe30024e522e7d34`.
- Branch quality gate: SUCCESS.
- Python syntax check: SUCCESS.
- P2/P3 quality gate: SUCCESS.
- Regression, compileall, pip check and dependency audit: SUCCESS.
- Browser/WebMCP live smoke: intentionally skipped because integration branch has no configured E2E credentials/public preview; this is not counted as a live-pass.
- Provider live smoke: intentionally skipped because integration branch has no provider tokens; no external provider data was changed.
- `main` remains untouched; integration branch is 23 commits ahead of main and 0 behind.
- Payments remain out of scope.
