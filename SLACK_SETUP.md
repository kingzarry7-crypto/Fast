# KING ZARRY AI — Slack integration

This integration is additive. It reuses the existing `AIEngine` and `SharedMemory` used by the other KING ZARRY AI platforms.

## Environment variables

Set these in the Railway service that runs the FastAPI backend:

- `SLACK_BOT_TOKEN` — Slack bot token beginning with `xoxb-`
- `SLACK_SIGNING_SECRET` — Slack app signing secret
- `MEMORY_DB_PATH` — keep the existing value; Slack uses the same shared memory database through `SharedMemory("slack", ...)`

No Slack secret belongs in GitHub.

## Slack app

Create a Slack app for the existing **King Zarry🇰🇷** workspace.

Under **OAuth & Permissions → Scopes → Bot Token Scopes**, add the minimum scopes for this build:

- `app_mentions:read`
- `chat:write`
- `im:history`

The Events API documents `app_mentions:read` for `app_mention` and `im:history` for `message.im`.

Under **Event Subscriptions**:

1. Turn on **Enable Events**.
2. Set the Request URL to:
   `https://YOUR-RAILWAY-BACKEND-DOMAIN/api/slack/events`
3. Subscribe to bot events:
   - `app_mention`
   - `message.im`

Install/reinstall the app to the workspace after changing scopes.

## Behavior

- In a channel: mention the bot, e.g. `@KING ZARRY AI hi`.
- In a direct message: send a normal message.
- Channel replies are posted in a thread.
- DM replies stay in the DM unless the incoming message is already threaded.
- The Slack user ID is passed to the existing AI engine, and the Slack memory namespace is `slack:<user_id>`.
- Slack retries are deduplicated by Slack's `event_id`.
- Slack request signatures are verified before processing.
- AI processing happens in a background thread so Slack receives its acknowledgement quickly.

## Health check

After deployment:

`GET /api/slack/health`

Expected when both secrets are configured:

`{"ok": true, "platform": "slack", "configured": true, ...}`

## Important

The code does not automatically add the bot to every channel. Invite the bot only to the channels where you want it to respond.
