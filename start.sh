#!/bin/bash
set -e

echo "═══════════════════════════════════════════════════════════════"
echo "👑 KING ZARRY AI — STARTING FULL STACK"
echo "═══════════════════════════════════════════════════════════════"

# Railway assigns PORT; fall back to 8000 for local runs
export PORT="${PORT:-8000}"

# ------------------------------------------------------------------
# 0) Browser runtime check.
#    Railway installs system Chromium from nixpacks.toml.
#    browser_operator.py uses /usr/bin/chromium automatically, so
#    never try to write Playwright browsers into protected
#    /usr/local/lib/python3.12/site-packages at runtime.
# ------------------------------------------------------------------
echo "🌐 Checking system Chromium..."
if [ -x "/usr/bin/chromium" ]; then
  echo "✅ System Chromium ready: /usr/bin/chromium"
elif command -v chromium >/dev/null 2>&1; then
  echo "✅ System Chromium ready: $(command -v chromium)"
else
  echo "⚠️ System Chromium was not found. Browser operator will be unavailable."
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
