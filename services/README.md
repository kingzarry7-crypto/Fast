# Backend services

Place new reusable business workflows here when they can be separated from transport and runtime startup.

Guidelines:
- Keep FastAPI route parsing and HTTP status mapping in `api.py` or future `controllers/` modules.
- Keep approval checks, permission enforcement, and evidence verification inside the actual workflow path; do not bypass them during extraction.
- Inject provider clients and configuration rather than reading credentials at import time.
- Keep database transactions and shared-memory boundaries explicit.
- Add tests for success, failure, authorization denial, and retry/idempotency behavior.

Existing modules remain at the repository root for now because the Railway launcher, bots, and runtime patches depend on their current import paths. Move code only in a dedicated, tested migration.
