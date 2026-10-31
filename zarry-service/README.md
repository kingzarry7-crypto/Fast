## Railway deployment status

A separate Railway service named `ZARRY` has been provisioned in the `Fast` project, isolated from the existing Fast/Kitty service. Its root directory is `/zarry-service`, Dockerfile is `Dockerfile`, persistent volume is mounted at `/models`, and its readiness check is `/ready`. The volume is 3 GB in the `sfo` region.

Railway variables are configured outside source control: `HF_HOME=/models/hf-cache`, `ZARRY_THREADS=2`, `ZARRY_CONTEXT_SIZE=4096`, `ZARRY_MAX_TOKENS=300`, `ZARRY_MODEL_REPO=unsloth/SmolLM3-3B-GGUF`, `ZARRY_MODEL_FILE_PATTERN=*Q4_K_M.gguf`, and an immutable `ZARRY_MODEL_REVISION`. `ZARRY_API_KEY` is stored as a Railway secret and must never be committed.

The service starts through `start.sh`, which downloads or reuses the model in the persistent cache and starts Uvicorn on Railway's `PORT`. `/ready` remains unhealthy until the model is loaded; `/health` is liveness. No GPU is configured. Measure peak memory and latency before selecting production capacity.

After the corrected Docker build succeeds and the service is healthy, generate a private/internal service URL or a protected public URL as appropriate, then run `python smoke_test.py` from a trusted environment with `ZARRY_SERVICE_URL` and `ZARRY_API_KEY`. The smoke test checks health, readiness, authentication and exact preservation of a synthetic `WAIT` assessment; it does not place orders.

Keep `ZARRY_ENABLED=false` in Fast until deployment, real-model smoke testing, latency/memory review and explicit approval are complete. ZARRY is explanation-only: Kitty remains the deterministic trading authority, and ZARRY cannot place orders or change Kitty's decision.

## Inference contract hardening

The service validates ISO-8601 timestamps with an explicit timezone. By default, market context older than 24 hours is rejected and timestamps more than 60 seconds in the future are rejected. Set `ZARRY_MAX_CONTEXT_AGE_SECONDS=0` only for controlled historical evaluation; do not use that override for live market context.

Responses include `X-Request-ID`, `X-ZARRY-Latency-Ms`, and `X-ZARRY-API-Version` headers. The readiness response reports the configured model repository and API version. Fast's proxy forwards a request ID and retries one transient connection failure only; it does not retry model timeouts.

Fast already mounts `/api/zarry/explain` behind the existing web-session authentication. It remains disabled unless `ZARRY_ENABLED=true`. The endpoint is an explicit, authenticated explanation request with schema bounds, freshness validation, rate limiting, and fail-closed response checks. It is not an automatic part of Kitty's signal generation or order path. Keep the flag false until the deployed authenticated smoke test, Fast-to-ZARRY private-network check, and acceptance review are complete.

Run contract tests with:

```bash
python -m unittest discover -s zarry-service/tests -p "test_*.py" -v
python -m unittest discover -s tests -p "test_zarry_api.py" -v
```
