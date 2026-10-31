# ZARRY inference service prototype

This is an isolated, optional explanation service. It is not part of Kitty's
signal engine and has no broker, order, market-data, or tool-execution access.

## Runtime configuration

- `ZARRY_MODEL_PATH`: local GGUF path. The exact model is deliberately not
  selected until the open-model benchmark is reviewed.
- `ZARRY_API_KEY`: required bearer token. The service refuses inference when
  this is missing.
- `ZARRY_THREADS`: CPU threads (default 2).
- `ZARRY_CONTEXT_SIZE`: context size (default 4096).
- `ZARRY_MAX_TOKENS`: response cap (default 300).

## Local run

```bash
cd zarry-service
pip install -r requirements.txt
export ZARRY_MODEL_PATH=/models/model.gguf
export ZARRY_API_KEY='set-a-long-random-secret'
uvicorn app:app --host 0.0.0.0 --port 8000
```

`GET /health` is liveness. `GET /ready` reports whether a model loaded.
`POST /v1/explain` requires `Authorization: Bearer <ZARRY_API_KEY>`.

The API validates the response schema, symbol, decision preservation, context
citations and numeric grounding. Invalid model output returns an error and is
not passed to Fast. Kitty's decision is copied from the request and cannot be
overridden by ZARRY. This prototype is not approved for production deployment.
