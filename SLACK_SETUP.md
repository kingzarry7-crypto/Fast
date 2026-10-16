# KING ZARRY AI — Slack integration

The Slack Events API is handled by the Railway FastAPI backend. The optional Cloudflare frontend route at `/api/webhooks/slack` is a thin proxy only; it forwards the raw request body and Slack signature headers unchanged to Railway. No Vercel service or Vercel credentials are required.

## Environment variables

Set these on the Railway service running the FastAPI backend:

- `SLACK_BOT_TOKEN` — Slack bot token beginning with `xoxb-`
- `SLACK_SIGNING_SECRET` — Slack app signing secret
- `MEMORY_DB_PATH` — retain the existing value so Slack uses the configured shared memory database

Do not commit secrets to GitHub.

## Slack app setup

Create or open the King Zarry AI Slack app.

Under **OAuth & Permissions → Bot Token Scopes**, add:

- `app_mentions:read`
- `chat:write`
- `im:history`

Under **Event Subscriptions**:

1. Enable Events.
2. Set the Request URL to either:
   - Direct to Railway: `https://YOUR-RAILWAY-BACKEND-DOMAIN/api/slack/events`
   - Through Cloudflare: `https://YOUR-CLOUDFLARE-FRONTEND-DOMAIN/api/webhooks/slack`
3. Subscribe to bot events `app_mention` and `message.im`.
4. Reinstall the app to the workspace after changing scopes.

The Cloudflare proxy does not validate or alter the body itself. Railway validates the original Slack signature, checks the timestamp, and deduplicates Slack event IDs.

## Behavior

- In a channel, mention the bot, e.g. `@King Zarry AI hi`.
- In a direct message, send a normal message.
- Channel replies are posted in a thread.
- DM replies stay in the DM unless the incoming message is already threaded.
- The Slack user ID is passed to the existing AI engine.
- Slack retries are deduplicated by Slack's `event_id`.
- Invalid or stale Slack signatures are rejected.
- AI processing happens in a background thread so Slack receives its acknowledgement quickly.

## Health check

After deployment, request:

`GET https://YOUR-RAILWAY-BACKEND-DOMAIN/api/slack/health`

When the bot token and signing secret are configured, the response should include `"configured": true`.

## Important

The code does not automatically add the bot to every channel. Invite the bot only to the channels where you want it to respond.
