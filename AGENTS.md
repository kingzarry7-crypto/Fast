# Base44 dev notes

- Run: `docker compose -f docker-compose.base44.yml up -d --build`. Services: `db` (postgres:16), `api` (FastAPI `api.py`, uvicorn --reload, image from `Dockerfile.base44-api` = deps only, source bind-mounted), `web` (Next.js dev in `frontend/`, port 3000).
- Single origin: `NEXT_PUBLIC_API_BASE_URL` is the public 3000 URL and `next.config.ts` rewrites `/api/*` and `/health` to `API_PROXY_TARGET` (http://api:8000). Keeps the lax session cookie same-origin. The rewrite only turns on when `API_PROXY_TARGET` is set, so Vercel/Railway prod isn't affected.
- DB schema: `web_database.sql` is loaded by postgres initdb on first boot only. Wipe the `pgdata` volume (`down -v`) to re-run it. The API creates some extra tables lazily.
- `.env.base44-defaults` sets `REQUIRE_EMAIL_VERIFY=false` because there's no Resend key locally. Signup works without email.
- Telegram/Discord bots (`bot.py`, `start.sh`) are not run in the preview. Only the web API and frontend run.
- The app boots with no API keys. Chat needs at least one of OPENROUTER/GROQ/GEMINI keys.
- Verify: `curl localhost:3000/health` should return `database.connected: true`. Then POST `/api/auth/register` through port 3000.
- Root `docker-compose.yml⁠` and `king_zarry_memory.db⁠` have a trailing invisible U+2060 in their filenames (harmless).
