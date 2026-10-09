# QA automation — AI Agent Content Manager

This branch adds a starter QA pipeline. It does not change application runtime code or production data, and excludes payments as requested.

## Local setup

```bash
python -m venv .venv
source .venv/bin/activate
python -m pip install --upgrade pip
pip install -r requirements.txt
pip install -r requirements-qa.txt
python -m playwright install chromium
pytest -m "not e2e" -v
```

For browser tests, configure `E2E_BASE_URL` to a dedicated test deployment and run `pytest -m e2e -v`.

## GitHub Actions

The unit/contract job runs on pushes and pull requests. Browser E2E runs only after repository variable `E2E_BASE_URL` is configured under **Settings → Secrets and variables → Actions → Variables**. Prefer a dedicated test deployment and tenant.

## Coverage and limitations

- The real `saas_core.data_load` query is tested with the HTTP data-access layer mocked, including tenant/entity filters.
- Supabase request headers, timeout, missing configuration, and HTTP error handling are tested without network calls.
- Static app-entrypoint and tenant-filter smoke checks are provided in a new file; existing app-specific smoke tests in this repository are preserved.
- Optional browser navigation checks detect HTTP 5xx responses and uncaught page errors.
- Authentication UI registration/reset flows and full CRUD for products, orders, CRM, inventory, and content planning still need deeper service/UI-specific tests.
- Telegram/VK send functions are not yet wired into mocked tests because their actual callable production adapters must be targeted; no messages are sent by this suite.
- Payments are intentionally excluded.

This is a starter suite, not a claim that all product flows are already verified.
