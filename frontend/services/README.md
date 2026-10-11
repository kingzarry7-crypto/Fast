# Frontend services

Use this directory for domain-oriented frontend/backend communication, for example chat, connectors/accounts, workflow approvals, markets, and memory/history.

Guidelines:
- Reuse the existing backend base URL, authentication/session behavior, timeout handling, and error normalization.
- Keep approval and evidence fields in typed contracts; never infer a successful action from an HTTP request merely being accepted.
- Keep UI state in components/hooks and request logic in services.
- Do not create a second competing API client. Extract from `frontend/lib/api.ts` gradually and preserve compatibility exports until callers are migrated.
- Add typed success/error contracts and tests for each extracted domain.
