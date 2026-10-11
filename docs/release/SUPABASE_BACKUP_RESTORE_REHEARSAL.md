# Supabase backup and restore rehearsal (manual)

This workflow is a preparation tool. It does not apply migrations to Production, change project settings, or enable payments.

## Automated validation

Pull requests changing the workflow run a secret-free test job. It verifies the explicit production dispatch guard, tests accepted/rejected synthetic connection-URI shapes, and runs a synthetic encryption/decryption round-trip plus checksum/HMAC tamper detection. These tests do not access the Production database, read repository secrets, or prove that the saved secret values are correct.

## Before running

In GitHub repository **Settings → Secrets and variables → Actions**, add repository secrets:

- `SUPABASE_DB_URL`: the database connection URI for Supabase project `lmdiwzkuvictysmdtuld`. Prefer the Session Pooler connection string. The workflow validates the host and username against the expected project without printing credentials. Do not put the URI in workflow inputs, code, issues, or logs.
- `BACKUP_ENCRYPTION_PASSPHRASE`: a unique random passphrase at least 24 characters long. Save it in an approved password manager. It is required to decrypt and authenticate the backup later. Do not reuse a GitHub or Supabase password.

Only a repository administrator should configure these secrets. Do not run this workflow from an untrusted fork or expose logs/secrets to third parties.

## Run it (after review and merge to the default branch)

1. Open **Actions → Supabase backup and restore rehearsal**.
2. Select **Run workflow** on the `main` branch.
3. Enter exactly `BACKUP_PRODUCTION` in the confirmation field.
4. The workflow checks that the connection URI points to the expected project, then performs a read-only database export and an isolated restore test.
5. Wait for both the export and isolated local restore steps to finish. If either fails, stop and investigate; do not treat the backup as verified.
6. If the workflow succeeds, download the encrypted archive and its SHA-256 checksum and HMAC sidecar. Copy them to approved encrypted storage outside GitHub and verify the checksum. The GitHub artifact expires after 7 days and is not a long-term backup.
7. Keep the passphrase separately from the encrypted backup and sidecars. Without it the backup cannot be decrypted or authenticated.

The workflow uses the current Supabase CLI setup action and Supabase-aware database dumps. It packages the SQL files locally, encrypts them with AES-256-CBC/PBKDF2, and verifies an HMAC-SHA256 over the encrypted archive before decrypting it for restore. Only the encrypted archive, checksum, and HMAC are uploaded; SQL dumps are not published as artifacts. It starts a disposable local Supabase stack on the GitHub-hosted runner and attempts a restore there. A restore failure must be investigated rather than waived; version/extension differences can require a compatible restore target. The runner is temporary, so the local restore target is destroyed after the job.

The production export job is guarded so it runs only for a manual dispatch on `main` with the exact confirmation value `BACKUP_PRODUCTION`. The pull-request validation job uses synthetic data and does not access secrets.

## Scope and limitations

- This workflow exports the database, not the actual Storage object files, deployed Edge Functions, Auth provider settings, SMTP settings, or application/provider secrets. Storage objects and operational configuration need separate, secure backups.
- The workflow creates an encrypted artifact retained for 7 days only. Copy it to approved encrypted off-site storage for durable recovery.
- A successful restore rehearsal proves only that this database dump could be restored into the disposable target used by that run. It does not prove that Storage objects, external integrations, payments, or the complete SaaS deployment can be recovered.
- It does not run the three pending billing migrations on Production.
- Resetting the database password can break other direct PostgreSQL connections that still use the previous password. The app's main data/auth flows use Supabase HTTPS API keys, but check any external direct-database clients and update them if necessary.
- Do not put the encryption passphrase or database connection URI in repository files or workflow inputs.

Official guidance: https://supabase.com/docs/guides/platform/migrating-within-supabase/backup-restore
