# King Zarry AI — Cloudflare-first deployment

Cloudflare Workers is the only production frontend target for King Zarry AI. Railway remains the API and bot backend. Vercel is retired as a deployment target; keep unrelated integrations that happen to use Vercel Connect separate from frontend hosting.

## Architecture

- Frontend: Cloudflare Workers + OpenNext
- Backend: Railway FastAPI
- Telegram/Discord workers: Railway
- Shared memory: Neon
- Canonical production frontend: https://kingzarry.bid/
- Cloudflare Workers fallback hostname: https://fast.kingzarry7.workers.dev/

The Next.js frontend proxies `/api/*` and `/health` to Railway through `next.config.ts`. The backend accepts the Cloudflare production origin; it does not need a Vercel deployment.

## Cloudflare build and deployment

In Cloudflare Dashboard → Workers & Pages, open the Worker connected to `kingzarry7-crypto/Fast`:

1. Root directory: `frontend`.
2. Production branch: use the branch you intend to deploy (normally `main` after the PR is reviewed and merged).
3. Build command: `npm run cf:build`.
4. Deploy command: `npx wrangler deploy`.
5. Set required frontend build variables/secrets in Cloudflare.
6. Set `API_UPSTREAM=https://fast-production-0eba.up.railway.app` if the backend URL has not changed.
7. Keep OAuth callback URLs pointed at the Railway callback endpoints configured in the provider consoles. OAuth return URLs must use the Cloudflare frontend origin.

## Verification checklist

From `frontend/`:

```bash
npm install
npm run typecheck
npm run lint
npm run cf:build
```

After deployment, verify on the Cloudflare URL:

- Landing page, login, registration and session persistence
- `/api/*` and `/health` proxying to Railway
- Chat and streaming behavior
- Market agent routing and data-unavailable handling
- Connected-account inventory and connector OAuth return
- Gmail approval/send flow (verify delivery evidence before saying sent)
- Shopify/GitHub connectors and approval queue
- Dashboard/workflows, voice and mobile layout

A green build is not proof of a successful production deployment. Confirm the Cloudflare Worker deployment status and run the live checks above.

## Retired deployment target

Do not use Vercel deployment status as a release gate for this project. Do not delete unrelated packages or routes solely because their names mention Vercel: the Slack Connect bridge is a separate integration, not the frontend host.
