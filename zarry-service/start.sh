#!/bin/sh
set -eu

# Railway volume should be mounted at /models.
export HF_HOME="${HF_HOME:-/models/hf-cache}"
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
exec uvicorn app:app --host 0.0.0.0 --port "${PORT:-8000}"
