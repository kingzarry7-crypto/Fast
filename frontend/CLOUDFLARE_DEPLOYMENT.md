# King Zarry AI — Cloudflare Workers frontend

This is an additive deployment path. The existing Vercel configuration is intentionally left intact.

## Architecture

- Frontend: Cloudflare Workers + OpenNext
- Backend: Railway FastAPI
- Telegram/Discord workers: Railway
- Shared memory: Neon

The frontend continues to proxy `/api/*` and `/health` to the Railway backend through `next.config.ts`.

## Cloudflare setup

In Cloudflare Dashboard:

1. Go to Workers & Pages.
2. Create a Worker and connect the GitHub repository `kingzarry7-crypto/Fast`.
3. Set the root directory to `frontend`.
4. Production branch: `main`.
5. Build command: `npm run cf:build`.
6. Deploy command: `npx wrangler deploy`.
7. Add the same production frontend environment variables currently used by Vercel under the Cloudflare Worker Build variables/secrets.
8. Keep `API_UPSTREAM` set to `https://fast-production-0eba.up.railway.app` unless the Railway backend URL changes.

## Important

Do not delete the Vercel project or its environment variables during migration.

First deploy to the generated `workers.dev` hostname and test:

- /
- /login
- /chat
- authentication/session cookies
- chat streaming
- /api/* proxying to Railway
- connected accounts
- Gmail approval/send flow
- dashboard/workflows
- voice/call UI
- mobile layout

Only after those checks pass should the production domain be moved from Vercel to Cloudflare.

## Local verification

From `frontend/`:

```bash
npm install
npm run typecheck
npm run build
npm run cf:build
npm run cf:preview
```

The normal `next` development/build scripts remain available for the existing Vercel deployment.

## Rollback

Because Vercel is not modified by this migration, rollback is simply keeping the domain pointed at Vercel and disabling/reverting the Cloudflare Worker deployment.
