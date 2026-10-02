# Security policy

## Secrets
Never commit Telegram, VK, Streamlit, or other credentials to the repository. Store them in Streamlit Secrets or GitHub Actions Secrets.

## Admin access
The application requires ADMIN_USERNAME and ADMIN_PASSWORD in Streamlit Secrets. The application fails closed when these secrets are missing.

## Reporting a security issue
Do not publish credentials or exploit details in a public issue. Contact the repository owner privately.

## Uploads
Product images are limited by extension, size, and image validation before being written to disk. Streamlit's global upload limit is 50 MB.

## CI
Every pull request to main runs Python syntax, dependency vulnerability, and Bandit static security checks.
