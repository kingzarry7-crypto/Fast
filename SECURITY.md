# Security Policy

## Reporting a vulnerability

Please do not publish sensitive security details in a public issue.

For a suspected vulnerability in KING ZARRY AI, contact the project owner privately with:
- a short description of the issue;
- affected component or endpoint;
- safe reproduction steps;
- potential impact.

Never include API keys, passwords, session cookies, OTPs, bot tokens, database credentials, or other secrets in an issue or pull request.

## Secrets

Runtime credentials must be supplied through environment variables or the hosting provider's secret store. Do not commit real values to the repository.

If a credential is accidentally committed, revoke or rotate it immediately and then remove it from repository history as appropriate.