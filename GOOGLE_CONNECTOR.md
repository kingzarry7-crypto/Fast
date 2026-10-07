# Google Workspace Connector

KZ now supports an official Google OAuth connector. It does not require the user to give KZ a Google password.

## Railway environment variables

Set these on the backend (Railway), not in GitHub:

- `GOOGLE_CLIENT_ID`
- `GOOGLE_CLIENT_SECRET`
- `GOOGLE_REDIRECT_URI`
- `GOOGLE_OAUTH_SCOPES` (optional)
- `CONNECTOR_STATE_SECRET` (already used by the existing connector layer)
- `KZ_CONNECTOR_ENCRYPTION_KEY` (already used by the existing connector layer)
- `FRONTEND_URL`

Recommended redirect URI:

`https://YOUR-BACKEND-DOMAIN/api/connectors/google/callback`

For this project, replace YOUR-BACKEND-DOMAIN with the current Railway backend hostname.

## Google Cloud setup

1. Create/select a Google Cloud project.
2. Enable Gmail API, Google Drive API, and Google Calendar API.
3. Configure the OAuth consent screen.
4. Create an OAuth 2.0 Client ID for a Web application.
5. Add the exact HTTPS redirect URI above.
6. Copy the client ID and client secret into Railway.

The connector requests narrow Workspace scopes for Gmail reading/sending, Drive metadata/file creation, and Calendar reading/event creation. Google may require OAuth app verification for sensitive/restricted scopes when the app is used beyond testing.

## KZ safety model

Read operations can run immediately:
- list recent Gmail messages
- list/search Drive files
- list upcoming Calendar events

Consequential operations always create an exact approval record first:
- send Gmail
- create Calendar event
- upload a text file to Drive

KZ executes only the exact approved payload, then requires provider evidence before reporting success.

OAuth access and refresh tokens are encrypted at rest and are never placed in KZ memory or returned to the frontend.
