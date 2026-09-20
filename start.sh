#!/bin/bash
set -e

echo "═══════════════════════════════════════════════════════════════"
echo "👑 KING ZARRY AI — STARTING FULL STACK"
echo "═══════════════════════════════════════════════════════════════"

# Railway assigns PORT; fall back to 8000 for local runs
export PORT="${PORT:-8000}"

# ------------------------------------------------------------------
# 1) FastAPI HTTP server (for Vercel frontend)
# ------------------------------------------------------------------
echo "🚀 Starting FastAPI on 0.0.0.0:${PORT}..."
uvicorn api:app --host 0.0.0.0 --port "${PORT}" --workers 1 &
API_PID=$!
echo "   → FastAPI PID: ${API_PID}"

# Give FastAPI a moment to bind so Vercel health checks don't race
sleep 3

# Sanity check — is the API actually alive?
if ! kill -0 "${API_PID}" 2>/dev/null; then
  echo "❌ FastAPI failed to start. Exiting."
  exit 1
fi

# ------------------------------------------------------------------
# 2) Telegram bot (also spawns Discord inside bot.py as a thread)
# ------------------------------------------------------------------
echo "🤖 Starting Telegram + Discord bot (bot.py)..."
python bot.py &
BOT_PID=$!
echo "   → Bot PID: ${BOT_PID}"

# ------------------------------------------------------------------
# 3) Keep container alive — if either process dies, exit so Railway
#    restarts the whole container (avoids half-dead states)
# ------------------------------------------------------------------
echo "═══════════════════════════════════════════════════════════════"
echo "✅ All services launched. Monitoring..."
echo "═══════════════════════════════════════════════════════════════"

# Wait for whichever dies first
wait -n "${API_PID}" "${BOT_PID}"
EXIT_CODE=$?

echo "⚠️ One service exited (code ${EXIT_CODE}). Shutting down the rest..."
kill "${API_PID}" "${BOT_PID}" 2>/dev/null || true
wait 2>/dev/null || true

exit "${EXIT_CODE}"
