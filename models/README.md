# Backend models

Place validated domain models and transport-independent schemas here as new code is added.

- Keep request/response validation separate from persistence details.
- Do not put credentials, session tokens, or mutable user state in model defaults.
- Keep compatibility with existing database schemas and stored records.
- Add explicit serialization tests before changing payload shapes.

Existing modules such as `workflow_models.py` remain in place until all imports and deployment entrypoints can be migrated together.
