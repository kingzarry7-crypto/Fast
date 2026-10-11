# Backend utilities

Place small, reusable, side-effect-light helpers here.

- Avoid network calls, database writes, and credential loading in generic utility functions.
- Keep provider-specific logic with its integration.
- Prefer explicit inputs/outputs and focused unit tests.
- Avoid importing the FastAPI app or bot launchers from utilities, which can create circular imports.
