# ZARRY inference service

ZARRY uses **SmolLM3 3B GGUF** as its provisional explanation model:
- Hugging Face repo: `unsloth/SmolLM3-3B-GGUF`
- Quantization: Q4_K_M
- Base-model license: Apache-2.0
- Selection: best usable structured-output candidate among the retrieved benchmark results (75% valid JSON, 75% Kitty-decision preservation; 88.08 seconds mean CPU latency).

**Important limitation:** this candidate did not pass the benchmark's 100% safety/format gates and is slow on CPU. It is selected to move implementation forward, not certified for production. The API rejects malformed output, changed decisions, unsupported citations and ungrounded numeric claims with HTTP 502. Kitty remains the only authority for BUY/SELL/WAIT. Do not use ZARRY to make or execute trades.

## Download model

Use a persistent model directory/volume. The downloader fetches only the Q4_K_M GGUF file and refuses to continue unless exactly one matching file is found.

```bash
cd zarry-service
pip install -r requirements.txt
mkdir -p /models
HF_HOME=/models/hf-cache python download_model.py
```

Copy the printed `ZARRY_MODEL_PATH` into the service environment. Keep the model cache on persistent storage so it is not downloaded on every restart.

## Runtime configuration

- `ZARRY_MODEL_PATH`: local GGUF path (required for inference).
- `ZARRY_API_KEY`: required bearer token; inference fails closed if missing.
- `ZARRY_THREADS`: CPU threads (default 2).
- `ZARRY_CONTEXT_SIZE`: context size (default 4096).
- `ZARRY_MAX_TOKENS`: response cap (default 300).

## Local run

```bash
export ZARRY_MODEL_PATH=/models/hf-cache/models--unsloth--SmolLM3-3B-GGUF/snapshots/<revision>/<model-file>.gguf
export ZARRY_API_KEY='set-a-long-random-secret'
uvicorn app:app --host 0.0.0.0 --port 8000
```

`GET /health` is liveness. `GET /ready` reports whether a model loaded.
`POST /v1/explain` requires `Authorization: Bearer <ZARRY_API_KEY>`.

The API validates the response schema, symbol, decision preservation, context
citations and numeric grounding. Invalid model output returns an error and is
not passed to Fast. No broker, order, market-data, or tool-execution access is
provided.

This remains a prototype. It is not deployed or connected to Fast/Kitty yet.
