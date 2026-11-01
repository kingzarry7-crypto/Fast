#!/bin/sh
set -eu

# Railway model cache volume is mounted at /models.
export HF_HOME="${HF_HOME:-/models/hf-cache}"
# Pin production inference to the approved Qwen3 1.7B artifact. This overrides
# any stale Railway variables left over from the retired SmolLM3 experiment.
export ZARRY_MODEL_REPO="unsloth/Qwen3-1.7B-GGUF"
export ZARRY_MODEL_FILE_PATTERN="Qwen3-1.7B-Q4_K_M.gguf"
export ZARRY_MODEL_REVISION="b2d17796e6fd93c353a0415a3abd8b7f801701de"
mkdir -p "$HF_HOME"

echo "ZARRY: resolving model artifact into persistent cache"
MODEL_OUTPUT="$(python download_model.py)"
printf '%s\n' "$MODEL_OUTPUT"
ZARRY_MODEL_PATH="$(printf '%s\n' "$MODEL_OUTPUT" | sed -n 's/^ZARRY_MODEL_PATH=//p' | tail -n 1)"
if [ -z "$ZARRY_MODEL_PATH" ] || [ ! -f "$ZARRY_MODEL_PATH" ]; then
  echo "ZARRY startup failed: model artifact was not resolved" >&2
  exit 1
fi
export ZARRY_MODEL_PATH

: "${ZARRY_API_KEY:?ZARRY_API_KEY must be configured}"
APP_PORT="${PORT:-8000}"

# Start the API locally, then prove the real model and authentication contract
# before leaving the process running for Railway's health checks.
uvicorn app:app --host 0.0.0.0 --port "$APP_PORT" &
SERVER_PID=$!
cleanup() {
  kill "$SERVER_PID" 2>/dev/null || true
}
trap cleanup EXIT INT TERM

python - "$APP_PORT" <<'PY'
import sys
import time
import requests

base = f"http://127.0.0.1:{sys.argv[1]}"
deadline = time.monotonic() + 240
while time.monotonic() < deadline:
    try:
        response = requests.get(base + "/ready", timeout=3)
        if response.status_code == 200 and response.json().get("model_loaded") is True:
            break
    except requests.RequestException:
        pass
    time.sleep(2)
else:
    raise SystemExit("ZARRY startup smoke failed: model did not become ready")
PY

ZARRY_SERVICE_URL="http://127.0.0.1:$APP_PORT" python smoke_test.py
wait "$SERVER_PID"
