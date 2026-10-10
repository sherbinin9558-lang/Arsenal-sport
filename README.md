# AI Content Manager

AI Content Manager — SaaS workspace for small businesses to manage products, content and sales operations from one place.

## Product

The application combines a shop workspace with AI-assisted content operations:

- product catalog and structured product data;
- AI-assisted product and content workflows;
- content generation for Telegram, Instagram and VK workflows;
- Reels/content production workflow;
- content calendar and planning;
- CRM, leads and order workflows;
- stock and product operations;
- analytics and operational dashboard;
- MAX operator workspace;
- tenant-isolated SaaS accounts with roles and permissions;
- Telegram publishing integration;
- subscription billing through T-Bank and YooKassa.

The product is designed as a reusable SaaS rather than a single-store website. Arsenal Sport is the historical repository name; the commercial product is **AI Content Manager**.

## Core workflow

`Products → Content → Publish → Leads/Orders → CRM → Analytics`

The catalog is the source of truth for product-related content. Content and sales workflows should reuse the same tenant-scoped product data instead of maintaining separate copies.

## SaaS architecture

- **Frontend/application:** Python + Streamlit
- **Database/authentication:** Supabase PostgreSQL + Supabase Auth
- **Tenant isolation:** PostgreSQL RLS and tenant-scoped application access
- **Payments:** T-Bank and YooKassa
- **Payment webhook:** FastAPI service in `tbank_webhook.py`
- **Hosting:** Streamlit Community Cloud for the Streamlit application; the billing webhook is deployed separately where a public FastAPI endpoint is available
- **Source control:** GitHub
- **Automation:** GitHub Actions

High-level flow:

```
Browser
  ↓
Streamlit / AI Content Manager
  ↓
Supabase Auth
  ↓
PostgreSQL + RLS
  ↓
Tenant-scoped products / CRM / content / analytics

Checkout
  ↓
T-Bank or YooKassa
  ↓
FastAPI billing webhook
  ↓
Provider API status verification
  ↓
Atomic Supabase billing state transition
```

## Security model

Production access is based on Supabase Auth and tenant isolation. Database tables use RLS policies, and server-side payment operations use the Supabase service-role key only on the server side.

Payment webhooks do not trust payment status supplied by the browser or notification body alone:

- T-Bank status is re-checked through the provider API;
- YooKassa status is re-checked through the provider API;
- successful T-Bank payments are additionally checked against the server-side tariff amount;
- billing state transitions are processed atomically and idempotently.

Secrets are never stored in the repository.

## Plans and billing

The application supports the plans:

- STARTER
- PRO
- BUSINESS

Actual prices are configured through production secrets/environment variables rather than hard-coded into the repository.

Before commercial launch, publish the real:

- prices;
- plan limits;
- renewal rules;
- cancellation rules;
- refund policy;
- supported payment providers;
- applicable legal documents.

## Local setup

Requirements:

- Python 3.x
- project dependencies from `requirements.txt`
- Supabase project for SaaS mode

Credentials are read from Streamlit Secrets or environment variables.

Do not commit real credentials. Use `.streamlit/secrets.toml` locally and keep it untracked. `secrets.example.toml` contains placeholders only.

Typical verification:

```bash
python -m unittest discover -s tests
python -m compileall .
```

## Production acceptance

The repository includes:

`docs/operations/PRODUCTION_ACCEPTANCE_CHECKLIST.md`

A green unit-test suite alone is not a production acceptance certificate. Final release requires operational evidence for the live deployment, backups/restore, monitoring, branch protection, CI and payment webhooks, plus legal/commercial documents.

## Commercial handover

A buyer should receive:

1. GitHub repository and ownership/transfer instructions;
2. Supabase project ownership and migration history;
3. Streamlit deployment configuration;
4. billing webhook deployment and provider configuration;
5. domain/URL configuration, if applicable;
6. list of production environment variables without exposing their secret values;
7. operational runbook and backup/restore procedure;
8. legal/commercial documents;
9. known limitations and open items.

The project should be transferred only after the production acceptance checklist is completed and the live configuration is documented.

## Repository status

The repository name remains `Arsenal-sport` for historical continuity. The customer-facing product identity is **AI Content Manager**.
