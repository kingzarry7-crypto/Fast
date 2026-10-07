#!/bin/bash
set -e

echo "═══════════════════════════════════════════════════════════════"
echo "👑 KING ZARRY AI — STARTING FULL STACK"
echo "═══════════════════════════════════════════════════════════════"

# Railway assigns PORT; fall back to 8000 for local runs
export PORT="${PORT:-8000}"

# Railway may inject PLAYWRIGHT_BROWSERS_PATH=0. Pin runtime to the same writable path used at build time.
export PLAYWRIGHT_BROWSERS_PATH="/app/.playwright"
echo "   → Runtime PLAYWRIGHT_BROWSERS_PATH=${PLAYWRIGHT_BROWSERS_PATH}"

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
# 1) FastAPI HTTP server (for Vercel frontend)
# ------------------------------------------------------------------
echo "🚀 Starting FastAPI on 0.0.0.0:${PORT}..."
uvicorn api:app --host 0.0.0.0 --port "${PORT}" --workers 1 &
API_PID=$!
echo "   → FastAPI PID: ${API_PID}"

sleep 3

if ! kill -0 "${API_PID}" 2>/dev/null; then
  echo "❌ FastAPI failed to start. Exiting."
  exit 1
fi

# ------------------------------------------------------------------
# 2) Telegram + Discord bot
# ------------------------------------------------------------------
echo "🤖 Starting Telegram + Discord bot (bot.py)..."
python bot.py &
BOT_PID=$!
echo "   → Bot PID: ${BOT_PID}"

echo "═══════════════════════════════════════════════════════════════"
echo "✅ All services launched. Monitoring..."
echo "═══════════════════════════════════════════════════════════════"

wait -n "${API_PID}" "${BOT_PID}"
EXIT_CODE=$?

echo "⚠️ One service exited (code ${EXIT_CODE}). Shutting down the rest..."
kill "${API_PID}" "${BOT_PID}" 2>/dev/null || true
wait 2>/dev/null || true

exit "${EXIT_CODE}"
