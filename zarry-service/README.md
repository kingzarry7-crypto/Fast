## Railway deployment status

A separate Railway service named `ZARRY` has been provisioned in the `Fast` project, isolated from the existing Fast/Kitty service. Its root directory is `/zarry-service`, Dockerfile is `Dockerfile`, persistent volume is mounted at `/models`, and its readiness check is `/ready`. The volume is 3 GB in the `sfo` region.

Railway variables are configured outside source control: `HF_HOME=/models/hf-cache`, `ZARRY_THREADS=2`, `ZARRY_CONTEXT_SIZE=4096`, `ZARRY_MAX_TOKENS=300`, `ZARRY_MODEL_REPO=unsloth/SmolLM3-3B-GGUF`, `ZARRY_MODEL_FILE_PATTERN=*Q4_K_M.gguf`, and an immutable `ZARRY_MODEL_REVISION`. `ZARRY_API_KEY` is stored as a Railway secret and must never be committed.

The service starts through `start.sh`, which downloads or reuses the model in the persistent cache and starts Uvicorn on Railway's `PORT`. `/ready` remains unhealthy until the model is loaded; `/health` is liveness. No GPU is configured. Measure peak memory and latency before selecting production capacity.

After the corrected Docker build succeeds and the service is healthy, generate a private/internal service URL or a protected public URL as appropriate, then run `python smoke_test.py` from a trusted environment with `ZARRY_SERVICE_URL` and `ZARRY_API_KEY`. The smoke test checks health, readiness, authentication and exact preservation of a synthetic `WAIT` assessment; it does not place orders.

Keep `ZARRY_ENABLED=false` in Fast until deployment, real-model smoke testing, latency/memory review and explicit approval are complete. ZARRY is explanation-only: Kitty remains the deterministic trading authority, and ZARRY cannot place orders or change Kitty's decision.