👑 KING ZARRY AI

Advanced Multi-Timeframe Trading & Intelligence Assistant
Telegram + Discord | AI Chat + Vision + Voice | Signals + News

King Zarry AI is a private VIP trading assistant built in Python. It combines multi-timeframe technical analysis (4H → 1H → 15M → 5M), economic calendar/news risk, strict market validation, and multi-provider AI failover to deliver advanced trading analysis and intelligence.

⸻

✨ Features

📊 Trading Engine

* Multi-Timeframe Analysis: 4H Major Regime → 1H Confirmation → 15M Primary Execution → 5M Entry Timing
* Late Entry & Exhaustion Detection: EARLY / ACCEPTABLE / LATE / EXTENDED
* Smart Signals: BUY/SELL/WAIT with Entry Zone, SL, TP1/TP2/TP3, Risk/Reward
* Assets: XAU/USD (Gold), BTC/USD, ETH/USD, SOL/USD
* One-Day Trade Planner: /plan BTC generates full daily plan
* Chart Generation: Matplotlib candles with EMA, levels, entry zones

🤖 AI Engine (ai_engine.py)

* Primary Provider: OpenRouter
* Fallback 1: Groq
* Fallback 2: Gemini
* Failover Chain: OpenRouter → Groq → Gemini
* OpenRouter API: https://openrouter.ai/api/v1
* Vision: Chart/image analysis where supported by the configured model
* Memory: Per-user isolated history (SQLite)
* TTS: ElevenLabs eleven_v3 with EdgeTTS female fallback
* Strict Validation Layer: EMA alignment (raw values), countertrend detection, SR proximity, real RR, confidence scoring

📰 News Engine (news_engine.py / news_monitor.py)

* Forex Factory / economic calendar scraping
* Risk levels: LOW / MEDIUM / HIGH / EXTREME
* Asset-specific news filtering
* Headlines + upcoming events integration into signals

💎 Telegram Bot (telegram_bot.py)

* Commands: /start, /help, /ask, /tts, /signal, /btc, /eth, /sol, /xau, /plan, /news, /events
* VIP Subscriptions: Telegram Stars (monthly, 3month, yearly)
* Payments: LabeledPrice, PreCheckout, successful_payment handler
* Database: king_zarry.db (users, subscriptions, payments, notifications)
* Admin: /users, /subscribers, /stats, /grant, /revoke, /broadcast, /notify
* JobQueue: Notification loop every 60s

💬 Discord Bot (bot.py)

* Discord.py with chart attachments
* Commands: !ask, !signal BTC, !plan XAU, mentions

⸻

📁 Project Structure

.
├── telegram_bot.py
├── bot.py
├── ai_engine.py
├── market.py
├── news_engine.py
├── news.py
├── news_monitor.py
├── memory.py
├── config.py
├── requirements.txt
├── king_zarry.db
└── king_zarry_memory.db

⸻

🚀 Quick Start

1. Install

pip install -r requirements.txt

2. Environment Variables

TELEGRAM_BOT_TOKEN=...
DISCORD_BOT_TOKEN=...
# AI Providers
# Primary → fallback 1 → fallback 2
OPENROUTER_API_KEY=...
GROQ_API_KEY=...
GEMINI_API_KEY=...
# OpenRouter
OPENROUTER_BASE_URL=https://openrouter.ai/api/v1
OPENROUTER_MODEL=openrouter/free
# Market Data
TWELVE_DATA_API_KEY=...
# Voice
ELEVENLABS_API_KEY=...
ELEVENLABS_VOICE_ID=hpp4J3VqNfWAUOO0d1Us
ELEVENLABS_MODEL_ID=eleven_v3
# Admin
ADMIN_IDS=123456,789012
DATABASE_PATH=king_zarry.db
MEMORY_DB_PATH=king_zarry_memory.db
MONTHLY_STARS=150

3. Run

# Telegram only
python telegram_bot.py
# Discord only
python bot.py

⸻

🔑 AI Provider Configuration

KING ZARRY AI uses a three-level AI failover system:

                 KING ZARRY AI
                       │
                       ▼
                 OpenRouter
                       │
                 ┌─────┴─────┐
                 │   fails   │
                 ▼           │
                   Groq
                 │
                 ┌─────┴─────┐
                 │   fails   │
                 ▼
                 Gemini

OpenRouter

OPENROUTER_API_KEY = clean_env_str(
    os.getenv("OPENROUTER_API_KEY")
)
OPENROUTER_BASE_URL = clean_env_str(
    os.getenv("OPENROUTER_BASE_URL"),
    "https://openrouter.ai/api/v1",
)
OPENROUTER_MODEL = clean_env_str(
    os.getenv("OPENROUTER_MODEL"),
    "openrouter/free",
)

OpenRouter provides an OpenAI-compatible API interface.

Existing compatibility aliases may remain in the codebase so older internal functions can continue working, but they do not mean the bot is using the OpenAI API.

Fallback Order

1. OpenRouter
2. Groq
3. Gemini

If OpenRouter fails, the AI engine attempts Groq.

If Groq fails, the AI engine attempts Gemini.

If all three providers fail, the bot returns its existing temporary-unavailable response instead of crashing.

No direct OpenAI or direct xAI API is required for the normal AI fallback chain.

⸻

💬 Commands

Telegram

/start - VIP status + menu
/help - Help and available commands
/buy - Show plans
/monthly - Monthly subscription
/3month - 3-month subscription
/yearly - Yearly subscription
/status - Subscription status
/history - AI conversation history
/paysupport - Payment support
/signal XAU - XAU/USD signal
/signal BTC - BTC/USD signal
/signal ETH - ETH/USD signal
/signal SOL - SOL/USD signal
/btc - Quick BTC signal
/eth - Quick ETH signal
/sol - Quick SOL signal
/xau - Quick XAU signal
/plan BTC - One-day BTC trade plan
/news BTC - BTC news risk
/events - Economic calendar
/ask What is RSI?
/tts Hello Zarry

Discord

!ask Explain gold structure
!signal BTC
!plan XAU
@King Zarry AI what is BTC doing?

⸻

🛡️ Validation Logic

ai_engine.py includes strict validation to avoid unreliable signals:

* Data integrity: price, ATR, EMA must be valid
* EMA alignment uses RAW values
* Threshold = max(0.08% price, 0.15 ATR)
* Countertrend penalty: BUY vs 4H BEARISH = -25 confidence
* Countertrend confidence capped at 74 unless strong evidence exists
* SR proximity: price <0.15% from resistance = RESISTANCE_BREAK_REQUIRED
* Entry status preserves the daily plan zone
* Entry is never automatically moved to the current price
* MISSED if price moves >2.5 ATR beyond the planned entry
* Real RR validation
* TP direction validation
* Confidence scoring with penalties and bonuses

⸻

📊 Database Schema

king_zarry.db

users(
    user_id,
    username,
    first_name,
    last_name,
    created_at
)
subscriptions(
    user_id,
    username,
    plan,
    expires_at,
    payment_method,
    payment_id
)
payments(
    id,
    user_id,
    plan,
    payment_method,
    payment_id,
    amount,
    currency
)
notifications(
    id,
    admin_id,
    message,
    interval_seconds,
    next_run,
    active
)

king_zarry_memory.db

Stores persistent AI/user conversation memory according to the bot’s memory implementation.

⸻

⚠️ Disclaimer

Algorithmic market analysis. Not financial advice. Use appropriate risk management. Past performance does not guarantee future results.

⸻

📄 License

Private - King Zarry AI. All rights reserved.

### One important correction
Your old README said:
**`xAI Grok-4 → Groq → Gemini → OpenRouter`**
That is definitely no longer what you want.
Your current documented architecture should be:
**`OpenRouter → Groq → Gemini`** ✅
And your `docker-compose.yml` should expose those same three AI credentials.
Also, `OPENROUTER_MODEL=openrouter/free` means **OpenRouter's free routing**, not specifically Grok. If your intention is for **Grok to be the model used inside OpenRouter**, then we should change that model value separately.
