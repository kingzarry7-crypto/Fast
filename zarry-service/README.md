# ZARRY inference service

ZARRY runs as a dedicated Railway service, isolated from the Fast/Kitty API. It uses the pinned Qwen3 1.7B Q4_K_M GGUF model, cached on the dedicated 4 GB Railway volume mounted at `/models`.

## Runtime

- Model repository: `unsloth/Qwen3-1.7B-GGUF`
- Immutable model revision: `b2d17796e6fd93c353a0415a3abd8b7f801701de`
- Model file: `Qwen3-1.7B-Q4_K_M.gguf`
- Cache: `HF_HOME=/models/hf-cache`
- Model runtime: `llama-cpp-python`, CPU inference
- Railway health check: `/ready` (returns ready only after the model is loaded)
- Liveness: `/health`

The Docker image must include `app.py`, `contract.py`, `general_chat.py`, `download_model.py`, `start.sh`, and `smoke_test.py`. The startup script downloads or reuses the pinned model, starts Uvicorn, waits for model readiness, and runs the authenticated synthetic-WAIT smoke test before leaving the service online.

## API contracts

- `POST /v1/explain`: authenticated explanation of an existing Kitty assessment. Kitty's exact symbol and decision are preserved by server-side validation. ZARRY cannot create a trading decision, access a broker, or place orders.
- `POST /v1/chat`: authenticated general-purpose chat. It is a separate conversation contract and has no Kitty decision or broker authority.
- `GET /metrics`: authenticated operational metrics.
- `GET /ready`, `GET /health`: readiness and liveness.

The general-chat router is packaged into the same image as the model service. Its system prompt explicitly denies trading-decision and broker authority. Both authenticated endpoints use the service's `ZARRY_API_KEY` secret; never commit secret values.

## Safety and operation

Kitty remains the sole trading decision authority. ZARRY is explanation-only for trading context and cannot place orders or alter risk settings. The general-chat endpoint is not part of Kitty's signal or order path. Keep the Fast-side `ZARRY_ENABLED` feature flag disabled until the Fast-to-ZARRY authenticated private-network integration and the full operational acceptance suite have been independently verified.

The production Qwen smoke test has verified health, readiness, rejection of unauthenticated requests, authenticated model-generated explanation, exact BTCUSD/WAIT preservation, expected citations, authority/mode markers, and absence of numeric claims. CPU inference latency is still being tuned; do not assume interactive chat latency from readiness alone.

## Tests

```bash
python -m unittest discover -s zarry-service/tests -p "test_*.py" -v
python -m unittest discover -s tests -p "test_zarry_api.py" -v
```
