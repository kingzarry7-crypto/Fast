# 👑 KING ZARRY AI

**Advanced Multi-Timeframe Trading & Intelligence Assistant**
Telegram + Discord + Web | AI Chat + Vision + Voice | Signals + News + Image/Video Generation

King Zarry AI is a private VIP trading assistant built in Python, with a Next.js web frontend deployed on Vercel and a Python backend deployed on Railway. It combines multi-timeframe technical analysis (4H → 1H → 15M → 5M), economic calendar/news risk, strict market validation, and multi-provider AI failover to deliver advanced trading analysis and intelligence across Telegram, Discord, and the web.

---

## ✨ Features

### 📊 Trading Engine
- **Multi-Timeframe Analysis**: 4H Major Regime → 1H Confirmation → 15M Primary Execution → 5M Entry Timing
- **Late Entry & Exhaustion Detection**: EARLY / ACCEPTABLE / LATE / EXTENDED
- **Smart Signals**: BUY/SELL/WAIT with Entry Zone, SL, TP1/TP2/TP3, Risk/Reward
- **Assets**: XAU/USD (Gold), BTC/USD, ETH/USD, SOL/USD
- **One-Day Trade Planner**: `/plan BTC` generates a full daily plan
- **Chart Generation**: Matplotlib candles with EMA, levels, entry zones

### 🤖 AI Engine (`ai_engine.py`)
- **Primary Provider**: OpenRouter
- **Fallback 1**: Groq
- **Fallback 2**: Gemini
- **Failover Chain**: OpenRouter → Groq → Gemini
- **OpenRouter API**: `https://openrouter.ai/api/v1`
- **Vision**: Chart/image analysis where supported by the configured model
- **Memory**: Per-user isolated history (SQLite on bots, Neon on web)
- **TTS**: ElevenLabs `eleven_v3` (Bella) with EdgeTTS female fallback
- **Strict Validation Layer**: EMA alignment (raw values), countertrend detection, SR proximity, real RR, confidence scoring

### 🎨 Image & Video Generation (Agnes AI)
- **Text-to-Image**: `agnes-image-2.0-flash`
- **Image Editing (image-to-image)**: `agnes-image-2.0-flash`
- **Text-to-Video**: `agnes-video-2.5`
- **Image-to-Video**: `agnes-video-2.5`
- **Natural Language Triggers**: `Draw a BTC chart`, `Create an image of gold bars`, `Make a video of a sunrise`
- **Explicit Video Commands** (Discord, via Fal.ai): `/textvideo`, `/imagevideo`

### 🌐 Live Web Search (Tavily)
- Real-time web search using the official Tavily SDK
- Credit-conserving: only triggers for genuinely current-information queries
- 5-minute cache, rate-limit-aware, timeout-safe
- Injects source titles and URLs into AI prompts — never fabricates citations

### 🎙️ Voice Notes (STT)
- **Primary**: Groq Whisper `large-v3`
- **Fallback**: OpenAI Whisper
- Transcribes Telegram voice/audio and Discord audio attachments
- Feeds transcription through the same pipeline as typed messages
- Temp files deleted immediately after transcription

### 📰 News Engine (`news_engine.py` / `news_monitor.py`)
- Forex Factory / economic calendar scraping
- Risk levels: LOW / MEDIUM / HIGH / EXTREME
- Asset-specific news filtering
- Headlines + upcoming events integrated into signals

### 🎬 Media Attachments (bot only)
- **Telegram** (`bot.py`): Text, voice, audio, photos (vision), documents
- **Discord** (`discord_bot.py`): Text, slash commands, voice channel TTS, image/video generation, audio STT

### 🌐 Web Frontend (Next.js on Vercel)
- Cyberpunk/Jarvis-style UI with animated AI core
- Public landing page (`/`), login (`/login`), register (`/register`)
- Protected routes: `/dashboard`, `/chat`, `/markets`, `/signals`, `/news`, `/settings`
- Voice input (Web Speech API) and AI voice read-out in chat
- Session auth via HttpOnly cookies

### 🔌 Web API (`api.py`, FastAPI on Railway)
- Neon PostgreSQL-backed authentication (scrypt password hashing, hashed session tokens)
- Endpoints:
  - `GET /` — status
  - `GET /health` — health check
  - `POST /api/auth/register`
  - `POST /api/auth/login`
  - `GET /api/auth/me`
  - `POST /api/auth/logout`
  - `POST /api/chat` — protected, uses web-only memory adapter

---

## 📁 Project Structure
