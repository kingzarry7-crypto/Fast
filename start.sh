#!/bin/bash
set -e

# Normalize legacy Railway environment-variable names that were accidentally
# created with a trailing space. Never print values; only report the variable name.
normalize_legacy_env() {
  local target="$1"
  local legacy="$2"
  local current_value
  current_value="$(printenv "$target" 2>/dev/null || true)"
  if [ -z "$current_value" ]; then
    local legacy_value
    legacy_value="$(printenv "$legacy" 2>/dev/null || true)"
    if [ -n "$legacy_value" ]; then
      export "$target=$legacy_value"
      echo "   → Normalized legacy environment variable name: $target"
    fi
  fi
}
normalize_legacy_env "GROQ_API_KEY" "GROQ_API_KEY "
normalize_legacy_env "GROQ_MODEL" "GROQ_MODEL "
normalize_legacy_env "ELEVENLABS_API_KEY" "ELEVENLABS_API_KEY "
normalize_legacy_env "ELEVENLABS_MODEL_ID" "ELEVENLABS_MODEL_ID "
normalize_legacy_env "FAL_KEY" "FAL_KEY "

echo "═══════════════════════════════════════════════════════════════"
echo "👑 KING ZARRY AI — STARTING FULL STACK"
echo "═══════════════════════════════════════════════════════════════"

# Railway assigns PORT; fall back to 8000 for local runs
export PORT="${PORT:-8000}"

# Railway may inject PLAYWRIGHT_BROWSERS_PATH=0. Pin runtime to the same writable path used at build time.
export PLAYWRIGHT_BROWSERS_PATH="/app/.playwright"
echo "   → Runtime PLAYWRIGHT_BROWSERS_PATH=${PLAYWRIGHT_BROWSERS_PATH}"

# Keep authenticated browser profiles on Railway persistent volume when it
# exists. An explicit BROWSER_PROFILE_DIR always wins; local/dev environments
# continue using the browser_operator.py fallback path.
if [ -z "${BROWSER_PROFILE_DIR:-}" ] && [ -d "/data" ] && [ -w "/data" ]; then
  export BROWSER_PROFILE_DIR="/data/browser_profiles"
fi
if [ -n "${BROWSER_PROFILE_DIR:-}" ]; then
  mkdir -p "${BROWSER_PROFILE_DIR}"
  echo "   → Browser profile persistence: ${BROWSER_PROFILE_DIR}"
else
  echo "   ⚠️ No persistent browser volume detected; authenticated website sessions may be lost when the container is replaced."
fi

# ------------------------------------------------------------------
# 0) Browser runtime check.
#    Prefer an explicitly configured/system browser, otherwise verify
#    the Chromium executable managed by Playwright during the image build.
#    This is diagnostic only; it never downloads browsers at runtime.
# ------------------------------------------------------------------
echo "🖥️ Configuring browser display..."
# Headless Chromium is substantially lighter on Railway. Screenshots and
# user-controlled browser interaction still work in headless mode.
if [ "${BROWSER_HEADLESS:-true}" = "false" ] && command -v Xvfb >/dev/null 2>&1; then
  export DISPLAY="${DISPLAY:-:99}"
  if ! pgrep -f "Xvfb ${DISPLAY}" >/dev/null 2>&1; then
    Xvfb "${DISPLAY}" -screen 0 1440x900x24 -nolisten tcp >/tmp/kz-xvfb.log 2>&1 &
    XVFB_PID=$!
    echo "   → Xvfb PID: ${XVFB_PID}, DISPLAY=${DISPLAY}"
    sleep 1
  fi
else
  export BROWSER_HEADLESS="true"
  echo "✅ Using lightweight headless Chromium (set BROWSER_HEADLESS=false only when a real display is required)."
fi

echo "🌐 Checking browser runtime..."
if [ -n "${BROWSER_EXECUTABLE_PATH:-}" ] && [ -x "${BROWSER_EXECUTABLE_PATH}" ]; then
  echo "✅ Configured Chromium ready: ${BROWSER_EXECUTABLE_PATH}"
elif [ -x "/usr/bin/chromium" ]; then
  export BROWSER_EXECUTABLE_PATH="/usr/bin/chromium"
  echo "✅ System Chromium ready: /usr/bin/chromium"
elif command -v chromium >/dev/null 2>&1; then
  export BROWSER_EXECUTABLE_PATH="$(command -v chromium)"
  echo "✅ System Chromium ready: ${BROWSER_EXECUTABLE_PATH}"
else
  echo "ℹ️ System Chromium not present; checking Playwright-managed Chromium..."
  python - <<'PY'
import os
from pathlib import Path

try:
    from playwright.sync_api import sync_playwright

    with sync_playwright() as p:
        exe = Path(p.chromium.executable_path)
        print(f"   → PLAYWRIGHT_BROWSERS_PATH={os.getenv('PLAYWRIGHT_BROWSERS_PATH', '(unset)')}")
        print(f"   → Playwright Chromium: {exe}")
        print(f"   → Exists: {exe.exists()}")

        if exe.exists():
            print("✅ Playwright-managed Chromium ready.")
        else:
            print("⚠️ Playwright-managed Chromium is missing. Browser operator will be unavailable.")
except Exception as e:
    print(f"⚠️ Browser runtime check failed: {type(e).__name__}: {e}")
PY
fi

# ------------------------------------------------------------------
# 1) FastAPI HTTP server (Railway backend API)
# ------------------------------------------------------------------
echo "🚀 Starting FastAPI on 0.0.0.0:${PORT}..."
uvicorn api:app --host 0.0.0.0 --port "${PORT}" --workers 1 &
API_PID=$!
echo "   → FastAPI PID: ${API_PID}"

wait_for_api() {
  local max_attempts=60
  local attempt=0
  while [ "$attempt" -lt "$max_attempts" ]; do
    if ! kill -0 "${API_PID}" 2>/dev/null; then
      echo "❌ FastAPI exited before becoming healthy."
      exit 1
    fi

    if python - "$PORT" <<'PY'
import json, sys, urllib.request
port = sys.argv[1]
url = f"http://127.0.0.1:{port}/health"
try:
    with urllib.request.urlopen(url, timeout=2) as resp:
        body = resp.read().decode("utf-8", errors="replace")
        print(body)
        raise SystemExit(0 if resp.status == 200 else 1)
except Exception:
    raise SystemExit(1)
PY
    then
      echo "✅ FastAPI /health check passed."
      return 0
    fi

    attempt=$((attempt + 1))
    sleep 1
  done

  echo "❌ FastAPI never became healthy on http://127.0.0.1:${PORT}/health"
  exit 1
}

wait_for_api

# ------------------------------------------------------------------
# 2) Telegram + Discord bot
# ------------------------------------------------------------------
start_telegram() {
  if [ -f "bot.py" ]; then
    echo "🤖 Starting Telegram bot (bot.py)..."
    python bot.py &
    BOT_PID=$!
    echo "   → Telegram bot PID: ${BOT_PID}"
  else
    echo "ℹ️ Telegram bot not started (bot.py missing)."
    BOT_PID=""
  fi
}

start_discord() {
  if [ -f "discord_bot.py" ] && [ -n "${DISCORD_BOT_TOKEN:-}" ]; then
    echo "💬 Starting Discord bot (discord_bot.py)..."
    python discord_bot.py &
    DISCORD_PID=$!
    echo "   → Discord bot PID: ${DISCORD_PID}"
  else
    echo "ℹ️ Discord bot not started (discord_bot.py missing or DISCORD_BOT_TOKEN not configured)."
    DISCORD_PID=""
  fi
}

start_telegram
start_discord

echo "═══════════════════════════════════════════════════════════════"
echo "✅ Services launched. Monitoring..."
echo "═══════════════════════════════════════════════════════════════"

health_check_api() {
  python - "$PORT" <<'PY'
import sys, urllib.request
port = sys.argv[1]
url = f"http://127.0.0.1:{port}/health"
try:
    with urllib.request.urlopen(url, timeout=2) as resp:
        if resp.status == 200:
            print(f"API health check ok: {resp.status}")
            raise SystemExit(0)
except Exception:
    pass
raise SystemExit(1)
PY
}

while true; do
  if ! kill -0 "${API_PID}" 2>/dev/null; then
    echo "⚠️ FastAPI exited unexpectedly. Shutting down bot processes..."
    kill "${BOT_PID}" 2>/dev/null || true
    if [ -n "${DISCORD_PID:-}" ]; then kill "${DISCORD_PID}" 2>/dev/null || true; fi
    wait 2>/dev/null || true
    exit 1
  fi

  if ! health_check_api; then
    echo "⚠️ FastAPI health endpoint is failing. Keeping process alive but logging degraded state."
  fi

  if [ -n "${BOT_PID:-}" ] && ! kill -0 "${BOT_PID}" 2>/dev/null; then
    echo "⚠️ Telegram bot process died. Restarting..."
    start_telegram
  fi

  if [ -n "${DISCORD_PID:-}" ] && ! kill -0 "${DISCORD_PID}" 2>/dev/null; then
    echo "⚠️ Discord bot process died. Restarting..."
    start_discord
  fi

  sleep 10
done
