# Security policy

## Scope

This repository contains the AI Content Manager application and its production security configuration.

## Reporting a vulnerability

Do not disclose credentials, access tokens, service-role keys, webhook secrets, or other sensitive material in a public issue.

Report suspected vulnerabilities privately to the repository owner with:
- affected component or endpoint;
- reproducible impact;
- minimal reproduction steps;
- suggested mitigation, when known.

## Incident response

1. Triage the report and determine whether customer or tenant data may be affected.
2. Immediately revoke or rotate any exposed credential.
3. Preserve relevant application, Supabase Auth, and webhook audit logs.
4. Contain the affected endpoint or capability without modifying unrelated production functionality.
5. Patch and test the affected code on a separate branch.
6. Verify tenant isolation, authentication, authorization, and regression tests.
7. Deploy the verified fix and document the incident, impact, root cause, and corrective actions.
8. Review whether additional secrets, sessions, or integrations require rotation.

## Production security controls

The production hardening gate includes:
- Gitleaks secret scanning;
- Bandit SAST;
- pip-audit dependency scanning;
- Supabase Security Advisor checks;
- RLS/integration tests;
- application-level authentication rate limiting;
- structured security audit events;
- Streamlit XSRF protection.

Supabase Auth controls such as leaked-password protection, CAPTCHA, session lifetime/inactivity controls, and platform-level rate limits are managed in the Supabase project settings and must remain enabled according to the production security checklist.

## Secret handling

Never commit:
- Supabase service-role or secret keys;
- webhook secrets;
- payment credentials;
- user passwords;
- refresh tokens;
- private API credentials.

Production secrets belong only in the deployment platform's secret store.
