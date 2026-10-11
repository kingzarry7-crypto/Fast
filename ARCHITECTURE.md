# King Zarry AI Architecture

This repository is a multi-runtime application. Keep deployment entrypoints stable while organizing code incrementally.

## Runtime boundaries

- **Web frontend:** `frontend/` — Next.js App Router, React, TypeScript, deployed to Cloudflare using OpenNext.
- **API/backend:** repository-root Python modules — FastAPI entrypoint `api.py`, launched by the existing Railway startup configuration.
- **Messaging bots:** `bot.py` (Telegram) and `discord_bot.py` (Discord), launched by the existing runtime launcher.
- **Shared state:** database and memory modules, including Neon-backed shared memory. Never create separate connector state stores just to reorganize files.
- **Static web files:** `frontend/public/` for files served by URL; `frontend/app/` remains the Next.js route tree.

## Frontend boundaries

- `frontend/app/`: route pages, layouts, and Next.js route handlers only.
- `frontend/components/`: reusable visual components; keep feature-specific UI in the existing feature folders.
- `frontend/hooks/`: React hooks.
- `frontend/lib/`: shared low-level utilities, constants, authentication helpers, and the existing API compatibility layer.
- `frontend/services/`: domain-oriented calls to the backend (chat, accounts/connectors, workflows, markets). Keep request/response contracts here; components should not duplicate fetch logic.
- `frontend/types/`: TypeScript domain contracts.
- `frontend/assets/`: assets imported by modules. Assets referenced by URL belong in `frontend/public/`.

Do not replace the existing API client all at once. Extract one domain at a time from `frontend/lib/api.ts`, retain compatibility exports during migration, and update callers only after the extracted service has the same behavior.

## Python backend boundaries

The Python runtime currently imports modules from the repository root. The folders `controllers/`, `services/`, `models/`, and `utils/` establish future ownership boundaries:

- `controllers/`: HTTP request/response handling and route registration.
- `services/`: business workflows and orchestration, independent of HTTP transport where practical.
- `models/`: validated domain data models and schemas (not database secrets or runtime state).
- `utils/`: pure, reusable helpers without side effects.
- Existing provider-specific integrations should remain in their current modules until imports and startup order can be migrated safely.

The folders do not authorize moving current root modules yet. In particular, preserve `api.py`, `launcher.py`, `bot.py`, and `discord_bot.py` entrypoints until a dedicated migration updates all imports and deployment commands.

## Change checklist

1. Preserve public API paths, request/response schemas, auth and approval checks.
2. Preserve Telegram/Discord startup and shared memory behavior.
3. Keep secrets in environment configuration; never commit real credentials.
4. Add or update tests with behavior changes.
5. Run frontend typecheck and Cloudflare build plus Python syntax/tests before merging.
6. Verify Cloudflare and Railway independently; a GitHub merge alone is not proof of deployment.
