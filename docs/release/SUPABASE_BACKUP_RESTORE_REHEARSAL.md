# Supabase backup and restore rehearsal (manual)

This workflow is a preparation tool. It does not apply migrations to Production, change project settings, or enable payments.

## Before running

In GitHub repository **Settings → Secrets and variables → Actions**, add repository secrets:

- `SUPABASE_DB_URL`: the database connection string for Supabase project `lmdiwzkuvictysmdtuld`. Prefer the Session Pooler connection string. Do not put it in workflow inputs, code, issues, or logs.
- `BACKUP_ENCRYPTION_PASSPHRASE`: a unique random passphrase at least 24 characters long. Save it in an approved password manager. It is required to decrypt the backup later. Do not reuse a GitHub or Supabase password.

Only a repository administrator should configure these secrets. Do not run this workflow from an untrusted fork or expose logs/secrets to third parties.

## Run it

1. Open **Actions → Supabase backup and restore rehearsal**.
2. Select **Run workflow**.
3. Enter exactly `BACKUP_PRODUCTION` in the confirmation field.
4. Wait for both the export and isolated local restore steps to finish.
5. If the workflow succeeds, download the encrypted artifact and its checksum. Copy it to encrypted storage outside GitHub and verify the checksum. The GitHub artifact expires after 7 days and is not a long-term backup.
6. Keep the passphrase separately from the encrypted backup. Without it the backup cannot be decrypted.

The workflow uses Supabase CLI database dumps and uploads only an encrypted archive; SQL dumps are not published as artifacts. It starts a disposable local Supabase stack on the GitHub-hosted runner and attempts a restore there. A restore failure must be investigated rather than waived; version/extension differences can require a compatible restore target. The runner is temporary, so the local restore target is destroyed after the job.

## Scope and limitations

- This workflow exports the database, not the actual Storage object files, deployed Edge Functions, Auth provider settings, SMTP settings, or application/provider secrets. Storage objects and operational configuration need separate, secure backups.
- The workflow creates an encrypted artifact retained for 7 days only. Copy it to approved encrypted off-site storage for durable recovery.
- A successful restore rehearsal proves only that this database dump could be restored into the disposable target used by that run. It does not prove that Storage objects, external integrations, payments, or the complete SaaS deployment can be recovered.
- It does not run the three pending billing migrations on Production.
- Do not put the encryption passphrase or database connection string in repository files or workflow inputs.

Official guidance: https://supabase.com/docs/guides/platform/migrating-within-supabase/backup-restore
