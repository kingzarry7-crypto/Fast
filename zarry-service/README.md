

## Railway deployment preparation (not deployed)

Configure a separate Railway service with root directory `/zarry-service`. Attach a persistent volume at `/models`; set `HF_HOME=/models/hf-cache`, `ZARRY_THREADS=2`, `ZARRY_CONTEXT_SIZE=4096`, and `ZARRY_MAX_TOKENS=300`. Set `ZARRY_API_KEY` only in Railway's secret environment, never in source control. Resolve an immutable Hugging Face commit and set `ZARRY_MODEL_REVISION` before production use; leaving it unset follows the repository's current default revision and is not reproducible.

The startup script downloads or reuses the model in the persistent cache, exports the resolved model path, requires `ZARRY_API_KEY`, and starts Uvicorn on Railway's `PORT`. The Railway health check uses `/ready`, which remains unhealthy until the model loads; `/health` is liveness. Allocate sufficient memory for the quantized 3B model and runtime, then measure peak usage before selecting production capacity. No GPU is configured.

After deployment is separately approved, run `ZARRY_SERVICE_URL=https://<service-domain> ZARRY_API_KEY='<secret>' python smoke_test.py` from a trusted environment. The smoke test checks health, readiness, authentication and exact preservation of a synthetic `WAIT` assessment; it does not place orders.

Keep `ZARRY_ENABLED=false` in Fast until deployment, real-model smoke testing, latency/memory review and explicit approval are complete. This change prepares configuration only: it does not create a Railway service, attach a volume, set environment values, deploy, merge, alter Vercel or enable the Fast proxy.
