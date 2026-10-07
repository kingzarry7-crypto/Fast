# KZ Official Connected Apps

KZ now supports an official connector path in addition to the existing browser fallback.

## How it works

1. The user chooses **Connect GitHub** in ACCOUNTS.
2. GitHub performs the login and authorization on GitHub itself.
3. KZ receives a provider token, encrypts it at rest, and never puts it into chat, memory, workflow text, screenshots, or audit details.
4. KZ uses the authorized GitHub API instead of trying to detect a logged-in browser page.
5. Read actions can run through the connector.
6. Consequential write actions create an exact one-time KZ approval.
7. After approval, KZ executes only that exact action and requires provider evidence before reporting success.
8. The user can disconnect the provider at any time.

This follows the same core pattern as modern connected-app systems: provider authorization determines access, app capabilities determine what can be done, and approval controls determine when an action runs.

## Railway environment variables

Set these on the backend:

- `GITHUB_CLIENT_ID`
- `GITHUB_CLIENT_SECRET`
- `GITHUB_REDIRECT_URI` — for example `https://YOUR-BACKEND-DOMAIN/api/connectors/github/callback`
- `CONNECTOR_STATE_SECRET` — long random secret, 32+ characters
- `KZ_CONNECTOR_ENCRYPTION_KEY` — long random secret, 32+ characters
- `FRONTEND_URL` — existing KZ frontend URL

Do not commit any of these values.

## GitHub OAuth app

Register the callback URL exactly as configured in `GITHUB_REDIRECT_URI`.

The initial connector requests the scopes configured by `GITHUB_OAUTH_SCOPES`; the default is `read:user repo`.

For a production-scale deployment, migrate the GitHub connector to a GitHub App with fine-grained repository permissions and short-lived user tokens.

## Browser fallback

The existing browser connection remains available for sites that do not have an official connector. It still enforces:

- manual login
- manual human verification
- no CAPTCHA/anti-bot bypass
- approval before consequential actions
- evidence verification before success

The browser path is now a fallback, not the primary account-connection architecture.
