# 👑 KING ZARRY AI

**Advanced Multi-Timeframe Trading & Intelligence Assistant**
Telegram + Discord | AI Chat + Vision + Voice | Signals + News

King Zarry AI is a private VIP trading assistant built in Python. It combines multi-timeframe technical analysis (4H → 1H → 15M → 5M), economic calendar/news risk, strict market validation, and multi-provider AI failover to deliver institutional-grade signals.

---

### ✨ Features

**📊 Trading Engine**
- Multi-Timeframe Analysis: 4H Major Regime → 1H Confirmation → 15M Primary Execution → 5M Entry Timing
- Late Entry & Exhaustion Detection: EARLY / ACCEPTABLE / LATE / EXTENDED
- Smart Signals: BUY/SELL/WAIT with Entry Zone, SL, TP1/TP2/TP3, Risk/Reward
- Assets: `XAU/USD (Gold)`, `BTC/USD`, `ETH/USD`, `SOL/USD`
- One-Day Trade Planner: `/plan BTC` generates full daily plan
- Chart Generation: Matplotlib candles with EMA, levels, entry zones

**🤖 AI Engine (`ai_engine.py`)**
- Provider: OpenRouter (`openrouter/free` via `https://openrouter.ai/api/v1/chat/completions`) with compatibility aliases for OpenAI
- Failover Chain: `xAI Grok-4 → Groq → Gemini → OpenRouter` (AUTO)
- Vision: Chart/image analysis via `meta-llama/llama-4-scout`
- Memory: Per-user isolated history (SQLite)
- TTS: ElevenLabs `eleven_v3` (Bella voice) with EdgeTTS female fallback
- Strict Validation Layer: EMA alignment (raw values), countertrend detection, SR proximity, real RR, confidence scoring

**📰 News Engine (`news_engine.py` / `news_monitor.py`)**
- Forex Factory / economic calendar scraping
- Risk levels: LOW / MEDIUM / HIGH / EXTREME
- Asset-specific news filtering
- Headlines + upcoming events integration into signals

**💎 Telegram Bot (`telegram_bot.py`)**
- Commands: `/start`, `/help`, `/ask`, `/tts`, `/signal`, `/btc`, `/eth`, `/sol`, `/xau`, `/plan`, `/news`, `/events`
- VIP Subscriptions: Telegram Stars (`monthly`, `3month`, `yearly`)
- Payments: `LabeledPrice`, PreCheckout, successful_payment handler
- Database: `king_zarry.db` (users, subscriptions, payments, notifications)
- Admin: `/users`, `/subscribers`, `/stats`, `/grant`, `/revoke`, `/broadcast`, `/notify`
- JobQueue: Notification loop every 60s

**💬 Discord Bot (`bot.py`)**
- Discord.py with chart attachments (not text-only)
- Commands: `!ask`, `!signal BTC`, `!plan XAU`, mentions

---

### 📁 Project Structure

```
.
├── telegram_bot.py      # Telegram bot - 100KB, polling, all handlers
├── bot.py               # Discord bot - standalone, with chart images
├── ai_engine.py         # AIEngine class, failover, validation (65KB)
├── market.py            # Market data, indicators, MTF logic
├── news_engine.py       # News & calendar engine
├── news.py / news_monitor.py # News monitoring helpers
├── memory.py            # User memory / SQLite
├── config.py            # Env cleaning helpers
├── requirements.txt
├── king_zarry.db        # Runtime: subscriptions, users
└── king_zarry_memory.db # Runtime: AI memory
```

---

### 🚀 Quick Start

**1. Install**

```bash
pip install -r requirements.txt
```

**2. Env (.env)**

```env
TELEGRAM_BOT_TOKEN=...
DISCORD_BOT_TOKEN=...

# AI Providers - at least one required
XAI_API_KEY=...
GROQ_API_KEY=...
GEMINI_API_KEY=...
OPENROUTER_API_KEY=...  # uses https://openrouter.ai/api/v1
OPENROUTER_MODEL=openrouter/free
OPENROUTER_URL=https://openrouter.ai/api/v1/chat/completions
OPENROUTER_BASE_URL=https://openrouter.ai/api/v1

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
```

**3. Run**

```bash
# Telegram only
python telegram_bot.py

# Discord only  
python bot.py
```

---

### 🔑 AI Provider Config

The project now uses **OpenRouter** as the OpenAI-compatible fallback:

```python
# ai_engine.py
OPENROUTER_API_KEY = clean_env_str(os.getenv("OPENROUTER_API_KEY"))
OPENROUTER_URL = "https://openrouter.ai/api/v1/chat/completions"
OPENROUTER_MODEL = "openrouter/free"

# Compatibility aliases - keeps existing code working
OPENAI_API_KEY = OPENROUTER_API_KEY
OPENAI_URL = OPENROUTER_URL
```

```python
# telegram_bot.py
OPENROUTER_BASE_URL = "https://openrouter.ai/api/v1"
OPENROUTER_API_KEY = OPENROUTER_API_KEY # alias
```

No secrets are hard-coded. Everything reads from env.

---

### 💬 Commands

**Telegram:**
```
/start - VIP status + menu
/buy - Show plans
/monthly, /3month, /yearly - Buy with Stars
/status, /history, /paysupport
/signal XAU / BTC / ETH / SOL
/btc, /eth, /sol, /xau - Quick signals
/plan BTC - One-day trade plan
/news BTC - News risk
/events - Economic calendar
/ask What is RSI?
/tts Hello Zarry
```

**Discord:**
```
!ask Explain gold structure
!signal BTC
!plan XAU
@King Zarry AI what is BTC doing?
```

---

### 🛡️ Validation Logic

`ai_engine.py` includes strict validation to avoid fake signals:

- Data integrity: price, ATR, EMA must be valid
- EMA alignment uses RAW values, threshold = max(0.08% price, 0.15 ATR)
- Countertrend penalty: BUY vs 4H BEARISH = -25 confidence, capped at 74 unless strong evidence
- SR proximity: price <0.15% from resistance = RESISTANCE_BREAK_REQUIRED
- Entry status: preserves daily plan zone, never moves entry to current price. MISSED if >2.5 ATR beyond
- Real RR: validates TP direction, calculates risk correctly
- Confidence: 0-100 with penalties/bonuses, not inflated

---

### 📊 Database Schema

**king_zarry.db**
- `users(user_id, username, first_name, last_name, created_at)`
- `subscriptions(user_id, username, plan, expires_at, payment_method, payment_id)`
- `payments(id, user_id, plan, payment_method, payment_id, amount, currency)`
- `notifications(id, admin_id, message, interval_seconds, next_run, active)`

---

### ⚠️ Disclaimer

> Algorithmic market analysis. Not financial advice. Use appropriate risk management. Past performance does not guarantee future results.

### 📄 License

Private - King Zarry AI. All rights reserved.
