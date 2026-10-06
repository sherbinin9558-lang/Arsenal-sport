# Production release runbook

## Release gate

A release is allowed only when the target commit has green regression, security, RLS, dependency, browser/WebMCP, provider-smoke and observability checks.

## Billing webhook

The billing webhook is a separate FastAPI service built from `Dockerfile.billing-webhook` and must expose:

- `GET /healthz` for liveness
- `GET /readyz` for configuration readiness
- provider webhook endpoints from `tbank_webhook.py`

The production deployment URL must be recorded as the provider callback URL. A source file or Dockerfile alone is not deployment evidence.

## Required production secrets

At minimum, configure the secrets required by the live-smoke workflow and the billing provider actually enabled in production. Never commit values to Git.

## Rollback

Application rollback is performed by redeploying the last known-good immutable commit. Database changes are forward-only unless a tested rollback migration exists. Before destructive schema changes, create and verify a backup.

## Backup/restore drill

Before commercial launch and at least quarterly:

1. create a production backup;
2. restore it into an isolated project/database;
3. run schema integrity and tenant-isolation tests;
4. verify representative tenant data counts and application reads;
5. record restore duration and result;
6. retain the evidence with the release record.

## Incident response

For billing, auth, tenant-isolation or data-loss incidents: disable the affected integration if needed, preserve audit evidence, identify affected tenants, restore service from the last known-good state, and document the incident and follow-up remediation.

## Release evidence

Record: commit SHA, CI run IDs, deployment URL, webhook readiness result, backup/restore evidence, and any manual checks that cannot be automated.
