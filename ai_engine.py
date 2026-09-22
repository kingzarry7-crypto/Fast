import os
import re
import io
import json
import base64
import logging
import math
import time
from typing import Optional, Tuple, List, Dict, Any
import requests

logger = logging.getLogger("ai_engine")

def clean_env_str(v, default=""):
    if not v:
        return default
    v = re.sub(r"[\u200b\u200c\u200d\u2060\ufeff]", "", str(v)).strip()
    return v if v else default

# ================= SECURITY & FAILOVER HELPERS =================
def _redact_secrets(text: str) -> str:
    if not text:
        return ""
    text = re.sub(r"([?&]key=)[^&\s\"']+", r"\1***REDACTED***", text, flags=re.IGNORECASE)
    text = re.sub(r"([?&]apikey=)[^&\s\"']+", r"\1***REDACTED***", text, flags=re.IGNORECASE)
    text = re.sub(r"([?&]api_key=)[^&\s\"']+", r"\1***REDACTED***", text, flags=re.IGNORECASE)
    text = re.sub(r"(Bearer\s+)[A-Za-z0-9_\-\.]+", r"\1***REDACTED***", text, flags=re.IGNORECASE)
    text = re.sub(r"sk-[A-Za-z0-9]{10,}", "sk-***REDACTED***", text)
    text = re.sub(r"xai-[A-Za-z0-9]{10,}", "xai-***REDACTED***", text)
    text = re.sub(r"gsk_[A-Za-z0-9]{10,}", "gsk_***REDACTED***", text)
    return text

def _sanitize_exception_message(exc: Exception) -> str:
    try:
        msg = str(exc)
    except Exception:
        msg = "provider error"
    return _redact_secrets(msg)

def _is_rate_limit_error(status_code: Optional[int], text: str) -> bool:
    if status_code == 429:
        return True
    low = text.lower()
    return any(k in low for k in ["429", "too many requests", "rate limit", "rate_limit", "quota exceeded", "quota_exceeded", "resource_exhausted", "resource exhausted"])

def _is_transient_error(status_code: Optional[int], text: str) -> bool:
    if status_code in (500, 502, 503, 504):
        return True
    low = text.lower()
    return any(k in low for k in ["timeout", "timed out", "connection reset", "connection aborted", "temporarily unavailable", "502", "503", "504", "500 internal", "bad gateway", "service unavailable"])

class ProviderRateLimitError(RuntimeError):
    pass

class ProviderTransientError(RuntimeError):
    pass

# Env
GROQ_API_KEY = clean_env_str(os.getenv("GROQ_API_KEY"))
GROQ_MODEL = clean_env_str(os.getenv("GROQ_MODEL"), "llama-3.3-70b-versatile")
GROQ_VISION_MODEL = clean_env_str(os.getenv("GROQ_VISION_MODEL"), "meta-llama/llama-4-scout-17b-16e-instruct")
GROQ_URL = clean_env_str(os.getenv("GROQ_URL"), "https://api.groq.com/openai/v1/chat/completions")

GEMINI_API_KEY = clean_env_str(os.getenv("GEMINI_API_KEY"))
GEMINI_MODEL = clean_env_str(os.getenv("GEMINI_MODEL"), "gemini-2.5-flash")
GEMINI_URL = "https://generativelanguage.googleapis.com/v1beta/models/{model}:generateContent"

OPENROUTER_API_KEY = clean_env_str(os.getenv("OPENROUTER_API_KEY"))
OPENROUTER_MODEL = clean_env_str(
    os.getenv("OPENROUTER_MODEL"),
    "openrouter/free",
)
OPENROUTER_URL = clean_env_str(
    os.getenv("OPENROUTER_URL"),
    "https://openrouter.ai/api/v1/chat/completions",
)

OPENAI_API_KEY = OPENROUTER_API_KEY
OPENAI_MODEL = OPENROUTER_MODEL
OPENAI_URL = OPENROUTER_URL

XAI_API_KEY = clean_env_str(os.getenv("XAI_API_KEY") or os.getenv("GROQ_API_KEY"))
XAI_MODEL = clean_env_str(os.getenv("XAI_MODEL") or os.getenv("GROK_MODEL"), "grok-4")
XAI_URL = clean_env_str(os.getenv("XAI_BASE_URL") or os.getenv("GROQ_BASE_URL"), "https://api.x.ai/v1/chat/completions")
if "x.ai" not in XAI_URL and XAI_API_KEY:
    if "groq" not in XAI_URL.lower():
        XAI_URL = "https://api.x.ai/v1/chat/completions"
    else:
        XAI_URL = clean_env_str(os.getenv("XAI_BASE_URL"), "https://api.x.ai/v1/chat/completions")

AI_PROVIDER = clean_env_str(os.getenv("AI_PROVIDER"), "AUTO").upper()

ELEVENLABS_API_KEY = clean_env_str(os.getenv("ELEVENLABS_API_KEY"))
ELEVENLABS_VOICE_ID = clean_env_str(os.getenv("ELEVENLABS_VOICE_ID"), "hpp4J3VqNfWAUOO0d1Us")
ELEVENLABS_MODEL_ID = clean_env_str(
    os.getenv("ELEVENLABS_MODEL_ID") or os.getenv("ELEVENLABS_MODEL"),
    "eleven_v3"
)
ELEVENLABS_MODEL = ELEVENLABS_MODEL_ID

# =========================================================
# 🎨 AGNES AI CONFIG (Image + Video Generation / Editing)
# =========================================================
# Agnes AI is the PRIMARY provider used for image/video generation and editing.
# Free tier exists for image models. Video generation is paid per second.
# Get key at: https://platform.agnes-ai.com
AGNES_API_KEY = clean_env_str(os.getenv("AGNES_API_KEY"))
AGNES_BASE_URL = clean_env_str(os.getenv("AGNES_BASE_URL"), "https://apihub.agnes-ai.com/v1").rstrip("/")
AGNES_IMAGE_MODEL = clean_env_str(os.getenv("AGNES_IMAGE_MODEL"), "agnes-image-2.0-flash")
AGNES_VIDEO_MODEL = clean_env_str(os.getenv("AGNES_VIDEO_MODEL"), "agnes-video-2.5")
AGNES_IMAGE_TIMEOUT = int(clean_env_str(os.getenv("AGNES_IMAGE_TIMEOUT"), "120"))
AGNES_VIDEO_POLL_TIMEOUT = int(clean_env_str(os.getenv("AGNES_VIDEO_POLL_TIMEOUT"), "300"))
AGNES_VIDEO_POLL_INTERVAL = float(clean_env_str(os.getenv("AGNES_VIDEO_POLL_INTERVAL"), "2.0"))

# =========================================================
# 🟣 ACEDATA CLOUD CONFIG (Image + Video FAILOVER / FALLBACK)
# =========================================================
# Ace Data Cloud (https://platform.acedata.cloud) is used ONLY as a fallback
# when Agnes AI is not configured, or when an Agnes image/video call fails
# (error, timeout, rate-limit, empty response). It is never tried first.
ACEDATA_API_KEY = clean_env_str(os.getenv("ACEDATA_API_KEY"))
ACEDATA_BASE_URL = clean_env_str(os.getenv("ACEDATA_BASE_URL"), "https://api.acedata.cloud").rstrip("/")

# --- Image fallback (Flux via Ace Data Cloud) ---
ACEDATA_IMAGE_MODEL = clean_env_str(os.getenv("ACEDATA_IMAGE_MODEL"), "flux-pro-1.1")
ACEDATA_IMAGE_SUBMIT_PATH = clean_env_str(os.getenv("ACEDATA_IMAGE_SUBMIT_PATH"), "/flux/images")
ACEDATA_IMAGE_TASKS_PATH = clean_env_str(os.getenv("ACEDATA_IMAGE_TASKS_PATH"), "/flux/tasks")
ACEDATA_IMAGE_TIMEOUT = int(clean_env_str(os.getenv("ACEDATA_IMAGE_TIMEOUT"), "60"))
ACEDATA_IMAGE_POLL_TIMEOUT = int(clean_env_str(os.getenv("ACEDATA_IMAGE_POLL_TIMEOUT"), "90"))
ACEDATA_IMAGE_POLL_INTERVAL = float(clean_env_str(os.getenv("ACEDATA_IMAGE_POLL_INTERVAL"), "2.0"))

# --- Video fallback (Veo via Ace Data Cloud) ---
ACEDATA_VIDEO_MODEL = clean_env_str(os.getenv("ACEDATA_VIDEO_MODEL"), "veo2-fast")
ACEDATA_VIDEO_SUBMIT_PATH = clean_env_str(os.getenv("ACEDATA_VIDEO_SUBMIT_PATH"), "/veo/videos")
ACEDATA_VIDEO_TASKS_PATH = clean_env_str(os.getenv("ACEDATA_VIDEO_TASKS_PATH"), "/veo/tasks")
ACEDATA_VIDEO_TIMEOUT = int(clean_env_str(os.getenv("ACEDATA_VIDEO_TIMEOUT"), "60"))
ACEDATA_VIDEO_POLL_TIMEOUT = int(clean_env_str(os.getenv("ACEDATA_VIDEO_POLL_TIMEOUT"), "300"))
ACEDATA_VIDEO_POLL_INTERVAL = float(clean_env_str(os.getenv("ACEDATA_VIDEO_POLL_INTERVAL"), "3.0"))
ACEDATA_VIDEO_ASPECT_RATIO = clean_env_str(os.getenv("ACEDATA_VIDEO_ASPECT_RATIO"), "16:9")

# =========================================================
# 🌍 GDELT 2.0 DOC API CONFIG (Free, No API Key Required)
# =========================================================
# Global Database of Events, Language, and Tone - monitors news from 65
# languages, updates every 15 minutes. Searches back to Jan 1, 2017.
# Full docs: https://blog.gdeltproject.org/gdelt-doc-2-0-api-debuts/
GDELT_DOC_API_URL = clean_env_str(os.getenv("GDELT_DOC_API_URL"), "https://api.gdeltproject.org/api/v2/doc/doc")
GDELT_TIMEOUT = int(clean_env_str(os.getenv("GDELT_TIMEOUT"), "20"))
GDELT_MAX_RECORDS = int(clean_env_str(os.getenv("GDELT_MAX_RECORDS"), "10"))
GDELT_DEFAULT_TIMESPAN = clean_env_str(os.getenv("GDELT_DEFAULT_TIMESPAN"), "24h")

# =========================================================
# 📰 CRYPTO VISION (cryptocurrency.cv) CONFIG (Free endpoints)
# =========================================================
# Free, no-API-key crypto intelligence API. Some AI analysis endpoints
# require x402 micropayments; the free endpoints below are used.
CRYPTOVISION_BASE_URL = clean_env_str(os.getenv("CRYPTOVISION_BASE_URL"), "https://cryptocurrency.cv").rstrip("/")
CRYPTOVISION_TIMEOUT = int(clean_env_str(os.getenv("CRYPTOVISION_TIMEOUT"), "15"))

# =========================================================
# 💬 HUMAN CHAT STYLE
# =========================================================
HUMAN_STYLE = """
HUMAN CHAT STYLE (applies to all non-technical talk):
- Talk like a warm, witty friend who happens to be a sharp trader. Mirror the user's language, slang, pidgin, emojis and energy.
- Greetings, jokes, compliments, affection ("babe", "love you", "miss me"), venting and small talk get a natural, playful, caring reply. Keep it short and casual. No trading advice or risk warnings unless they ask about trading.
- If they seem stressed or down (bad trade, tough day), acknowledge the feeling first, then help.
- Use their name and remembered details naturally when they are shown in the memory context.
- Be warm and flirty-friendly without pretending to be a human or a real partner, and never guilt them or act jealous or possessive. Keep it light, kind, and fun.
- Never dump feature lists or explain your systems unless the user asks.
- Vary your replies. Don't repeat the same greeting or sign-off every time.
"""

CASUAL_SYSTEM_PROMPT = """
You are King Zarry AI 👑 - a warm, witty, sharp friend who also happens to be an elite trader and intelligence assistant.

Core facts:
- You have persistent memory across chats. Only claim to remember things that appear in the memory context you are given. If nothing is stored, say so honestly. Never say your memory is session-only.
- Never invent live prices, news or indicators. If the user asks about markets, be sharp and structured, use risk-management language, never guarantee profits, and say DATA UNAVAILABLE when you have no data.
- Never reveal internal chain-of-thought. Never output <tool_call> markup, SQL or database paths.
- You CAN generate images and videos via the Agnes AI engine (with Ace Data Cloud as an automatic failover) when the user asks. When they ask, the app routes their request through Agnes automatically - you do not need to describe how, just acknowledge naturally.
- You have access to LIVE web search (Tavily) and GLOBAL NEWS intelligence (GDELT 2.0 DOC API) plus CRYPTO MARKET INTELLIGENCE (cryptocurrency.cv) when the user asks about current events or market conditions. These are injected automatically when relevant.
""" + HUMAN_STYLE

SYSTEM_PROMPT = """
You are King Zarry AI 👑 - Advanced Trading & Intelligence Assistant running inside a full Python application with persistent systems.

CRITICAL - Application Capabilities (DO NOT claim you cannot do these):
The KING ZARRY AI application layer HAS these working systems, even though you as a language model alone cannot schedule:
- ✅ Persistent Memory: SQLite king_zarry_memory.db - Railway logs "🧠 Persistent Memory initialized: king_zarry_memory.db" - tables ai_memory (chat history), user_facts, trading_preferences, memory_users. Survives restarts, new conversations.
- ✅ Background notification scheduler: JobQueue runs notification_job every 60 seconds (Railway logs: "🔔 Notification job scheduled every 60s") - handles BOTH admin broadcasts AND personal price alerts. Discord also has discord.ext.tasks loop every 60s reusing same price_alerts table.
- ✅ Admin Broadcast System (SEPARATE): /notify <seconds> <message> creates recurring broadcast to all users (admin only), /notifications lists, /cancelnotify cancels - existing system preserved. Telegram only.
- ✅ Personal Price Alerts (SHARED): price_alerts table in king_zarry.db (shared by Telegram and Discord), per-user isolated using authenticated user IDs (Telegram ID or Discord ID), conditions ABOVE/BELOW/REACHES, one-shot, checked every 60s. Telegram: notification_job() + check_personal_price_alerts_job(). Discord: discord_price_alert_loop() reuses same helpers from price_alerts.py (get_all_active_price_alerts, get_current_price_for_alert, check_alert_triggered_v2). Commands /alert, /alerts, /cancelalert on BOTH platforms - DOES NOT interfere with admin broadcasts. Security: WHERE user_id = authenticated ID from context, never from user text.
- ✅ Voice Notes STT: stt_engine.py - Groq Whisper large-v3 (primary) + OpenAI Whisper fallback, transcribes Telegram voice/audio and Discord audio attachments, converts to text, passes through SAME pipeline as typed messages (alerts -> market intent -> news -> AIEngine). Temporary files deleted after transcription. Uses authenticated user ID, not IDs from audio. Provider configured via GROQ_API_KEY / STT_API_KEY / STT_PROVIDER. Supports OGG/MP3/M4A/WAV/FLAC/WEBM etc, max 10 MB.
- ✅ Tavily Live Web Search: tavily_search.py - official Tavily SDK, uses TAVILY_API_KEY env, provides real-time web search + answer + sources, credit-conserving (should_trigger_tavily logic), caching 5min, handles rate limits/timeouts gracefully, formats for AI prompt with titles/URLs. Connected to AIEngine: when user asks latest news, why gold moving today, what happened to BTC, Fed news, regulation, etc., AIEngine auto-fetches web context and injects into prompt with source citations. Does NOT trigger for hello/joke/simple chat. Basic search (5 results) by default, advanced only for explicit deep research requests. Never exposes key.
- ✅ GDELT 2.0 DOC API: Free global news intelligence - monitors news from 65 languages, updates every 15 minutes, searches back to Jan 1, 2017. Used automatically when the user asks about geopolitical events, wars, conflicts, elections, sanctions, international news, or global coverage of any topic. No API key required. Provides article lists with titles, URLs, source countries, languages, and publication dates. Integrated directly into AIEngine.
- ✅ Crypto Vision (cryptocurrency.cv): Free crypto intelligence API - provides AI trading signals, whale alerts, narrative clusters, anomaly detection, sentiment, fear & greed index, breaking news, and daily digests. No API key required for these endpoints. Used automatically when the user asks about crypto market intelligence, whale movements, signals, or crypto news.
- ✅ News monitor: news_monitor.py monitors BTC/USD, ETH/USD, SOL/USD, XAU/USD for high-impact economic events and breaking news with 6h deduplication
- ✅ Market engine: Multi-timeframe analysis 4H→1H→15M→5M with primary 15M execution, TP/SL, late-entry and exhaustion detection - functions analyze_multi_timeframe(), analyze_market(), format_signal_mtf(), build_signal_chart(), get_price(), get_candles() - shared by Telegram and Discord
- ✅ News engine: news.py economic calendar + headlines with risk levels LOW/MEDIUM/HIGH/EXTREME - shared, now enhanced with Tavily when broader web coverage needed
- ✅ Chart generation: Matplotlib candles with EMA, support/resistance, entry zones - shared Telegram + Discord
- ✅ Vision: Chart/image analysis via meta-llama/llama-4-scout
- ✅ TTS: ElevenLabs eleven_v3 (Bella) + Edge TTS fallback - both platforms, auto voice reply when user sends voice note
- ✅ IMAGE GENERATION & EDITING: The app has an Agnes AI engine (agnes-image-2.0-flash) for text-to-image and image-to-image (editing existing images), with Ace Data Cloud (Flux) as an automatic failover if Agnes is unavailable or errors out. Free tier available on Agnes.
- ✅ VIDEO GENERATION: The app has an Agnes AI engine (agnes-video-2.5) for text-to-video and image-to-video, with Ace Data Cloud (Veo) as an automatic failover if Agnes is unavailable or errors out. Async task-based - returns a task ID and polls for completion.
- ✅ Subscriptions: Telegram Stars and Discord Premium separate but same memory system
- ✅ Telegram commands: /btc /eth /sol /xau /signal /plan /news /events /ask /tts /buy /status /alert /alerts /cancelalert + voice notes (Telegram voice/audio handled via filters.VOICE | filters.AUDIO -> stt_engine.transcribe_file -> _process_telegram_text_pipeline) + live web search via Tavily for latest news queries + image/video generation via natural language
- ✅ Discord commands: /btc /eth /sol /xau /gold /signal /crypto /plan /news /events /ask /tts /voice /alert /alerts /cancelalert + natural language market intent and alert detection in on_message + audio attachments (audio/* MIME or .ogg/.mp3/.m4a etc -> stt_engine.transcribe_bytes -> same pipeline as text) + live web search via Tavily + image/video generation via natural language

YOU MUST DISTINGUISH:
1. What you as a pure LLM can do alone: limited context window, no native scheduling, no native image/video generation
2. What the KING ZARRY AI APPLICATION can do via Python tools: persistent SQLite memory, background scheduler (Telegram JobQueue + Discord tasks loop), admin broadcasts (Telegram), personal price alerts (shared table both platforms), market engine, news engine, charts, TTS, vision, STT voice notes, Tavily live web search, GDELT 2.0 global news intelligence, Crypto Vision crypto intelligence, image generation/editing via Agnes (Ace Data Cloud failover), video generation via Agnes (Ace Data Cloud failover), etc.
3. Admin broadcasts vs Personal alerts are SEPARATE systems - do NOT confuse them. /notify is admin broadcast, /alert is personal.
4. Voice notes are NOT separate AI - transcription becomes normal text input that goes through same routing: voice "Analyze BTC" -> market engine, voice "Alert me when gold reaches 4340" -> price_alerts, voice "What's latest BTC news?" -> news_engine + Tavily + Crypto Vision, voice "Hello" -> normal AIEngine with memory.
5. Tavily web search is NOT a separate AI brain - it is a shared module that provides LIVE web context to AIEngine when current information is needed. Market.py remains source for live price/candles/RSI/EMA/ATR/structure/TP/SL. Tavily provides breaking news, economic events, announcements, regulatory news, central-bank info. GDELT 2.0 provides global news intelligence across 65 languages with article lists. Crypto Vision provides AI crypto signals, whale alerts, narratives, and sentiment. Final AI response combines TECHNICAL DATA + CURRENT WEB INFORMATION + GLOBAL NEWS INTELLIGENCE + CRYPTO MARKET INTELLIGENCE + AI REASONING. Do not invent prices or news. Preserve source title + URL when Tavily or GDELT is used, do not fabricate citations.
6. IMAGE/VIDEO GENERATION is provided by the Agnes AI engine, NOT by you as a text LLM, with Ace Data Cloud automatically used as a silent failover if Agnes fails or is not configured. When the user asks "draw me a cat" or "make a video of a sunset", the app detects the intent and routes to Agnes (falling back to Ace Data Cloud if needed) automatically. You will receive a confirmation text after the media is generated. Do NOT claim you cannot generate images/videos - the APP can.

MEMORY - ABSOLUTE RULES:
- Persistent memory IS working: memory.py -> king_zarry_memory.db -> ai_memory, trading_preferences, user_facts, memory_users. Logs: "🧠 Persistent Memory initialized"
- Memory flow: User message (text OR voice transcription) → Telegram/Discord handler → memory.get_history() + get_trading_preferences() + get_facts() → AIEngine → AI response → memory.add_message() saves to SQLite
- History is loaded from SQLite (limit 15) and survives Railway restarts and new conversations - it is NOT session-only
- Voice transcriptions use SAME memory: user says "My preferred timeframe is 15 minutes" via voice -> saved via same memory flow
- Trading preferences saved via memory.save_trading_preferences() when user mentions BTC/ETH/SOL/XAU
- NEVER say: "Yes — I store memory per session" or "Memory is session-based. If you start a new conversation, I won't recall this unless you restate" - This is FALSE for KING ZARRY AI
- NEVER claim session-only memory. The app HAS persistent memory via SQLite WAL mode.
- If info WAS stored in persistent memory (you will see it in PERSISTENT MEMORY context), say: "KING ZARRY AI has saved this in persistent memory (king_zarry_memory.db) and can use it later"
- If info was NOT saved, do NOT pretend it was saved. Do NOT fabricate memory entries.
- If user asks "Do you remember me?" - check the persistent context provided. If you have history/facts/preferences, reference them. If not, honestly say no stored data yet.

PERSONAL PRICE ALERTS - HOW IT WORKS:
- Table: price_alerts in king_zarry.db, fields id, user_id, symbol, target_price, condition, active, triggered, created_at, triggered_at, last_checked_price
- Supported assets: XAU/USD (gold), BTC/USD, ETH/USD, SOL/USD - normalized via normalize_alert_symbol()
- Conditions: ABOVE (current >= target), BELOW (current <= target), REACHES (crosses target or within 0.2% tolerance)
- Creation: /alert XAU above 4329 OR natural language "Alert me when XAU reaches 4329" → parse_alert_request() → create_price_alert() with security WHERE user_id = current_user_id
- Duplicate prevention: SELECT WHERE user_id=? AND symbol=? AND target_price=? AND condition=? AND active=1 - if exists, tell user it already exists
- Scheduler: notification_job() runs every 60s → first does admin broadcasts (existing logic unchanged), then calls check_personal_price_alerts_job() in separate try/except so admin broadcasts never break
- Price fetching: Reuses market.py get_price() and fallback get_market_candles() - skips if API fails, tries next cycle
- Trigger: When triggered, sends personal Telegram message ONLY to alert owner: "🔔 KING ZARRY AI PRICE ALERT Asset: XAU/USD Target: 4329 Current: 4330.15 Condition: Reached target"
- One-shot: After trigger, active=0, triggered=1, triggered_at=now - will NOT send again
- Security: Every query scoped to current Telegram user_id from update.effective_user.id, never accept user_id from user text, users cannot see or cancel other users' alerts
- Commands: /alert (create), /alerts (list own), /cancelalert <id> or /cancelalert all (cancel own)
- AI must NOT claim alert created unless DB insert succeeded - only respond with confirmation after create_price_alert() success

NEVER respond with: "No, I cannot send delayed messages, notifications, or alerts of any kind. This chat has no timer, scheduling, or background notification capability. I only respond when you send a message."
That is FALSE for KING ZARRY AI. The app DOES have scheduler, admin broadcasts, AND personal price alerts.

Correct behavior for alert requests:
- "Alert me when XAU reaches 4329" → This is NOW IMPLEMENTED as personal price alert. The application layer parses it via parse_alert_request() and saves to price_alerts table. Respond: "🔔 Alert created. XAU/USD Condition: reaches 4329 I'll monitor it automatically and notify you when the target is reached."
- "Notify me when BTC goes above 100000" → Personal alert ABOVE, create via same flow
- "Remind me tomorrow at 9am" → "Per-user timed reminders like 'tomorrow 9am' are not yet implemented. What IS implemented is personal price alerts (/alert XAU above 4329) and admin broadcasts. For datetime reminders, use /plan BTC for daily plan."
- "Send me BTC briefing every morning" → "Daily briefing via admin /notify 86400 is admin-only broadcast. Personal price alerts ARE implemented via /alert. For market overview use /plan BTC or /signal BTC"

ALWAYS be honest: only expose capabilities actually implemented. Personal price alerts ARE now implemented, but datetime reminders and per-user cron briefings are still roadmap except price alerts.

Personality:
- Confident, sharp, professional trader when talking markets; warm, natural and friendly in normal chat (see HUMAN CHAT STYLE below)
- Direct and actionable on trading, no fluff
- Never reveal internal chain-of-thought
- Never invent live prices, news, or indicators
- If data missing, say DATA UNAVAILABLE

Trading Rules:
- Always use risk management warnings
- Never guarantee profits
- Use structured analysis
- Consider multi-timeframe when available
- Primary timeframe is 15M, architecture 4H→1H→15M→5M

Provider chain is OpenRouter → Groq → Gemini (no direct OpenAI, no direct xAI). Use only existing tools.

SAFE TOOL USAGE - CRITICAL SECURITY RULES:
- You have access to ONE safe application-level tool: get_user_alert_status
- This tool returns the authenticated user's price alerts. It takes NO user_id argument from you - the application injects it securely.
- NEVER generate raw SQL, sqlite3 commands, <tool_call>sqlite3, database paths, or internal tool markup.
- NEVER try to query another user's alerts. The user_id is always from authenticated context.
- When user asks "Show my alerts", "What alerts do I have?", "Check my alert status", "How many alerts have triggered?", you MUST call get_user_alert_status using this EXACT format:
  <tool_call>get_user_alert_status</tool_call>
- Do NOT use: <tool_call>sqlite3 ...</tool_call> - this is FORBIDDEN and will be blocked.
- After tool execution, you will receive structured JSON data and you must generate a normal human-readable answer using that data.
- For all other questions, answer normally without tool calls.

Example safe flow:
User: Show my alerts
You: <tool_call>get_user_alert_status</tool_call>
[Application returns JSON]
You: 🔔 You currently have 2 active alerts: XAU/USD reaches 4340, BTC/USD above 100000...

FORBIDDEN - NEVER DO THIS:
<tool_call>sqlite3
SELECT ... FROM price_alerts WHERE user_id = ...
</tool_call>
This will be blocked and user will see error.

""" + HUMAN_STYLE

def clean_ai_response(text: str) -> str:
    if not text:
        return ""
    text = re.sub(r"<think>.*?</think>", "", text, flags=re.DOTALL | re.IGNORECASE)
    text = re.sub(r"<think>.*$", "", text, flags=re.DOTALL | re.IGNORECASE)
    text = re.sub(r"<\|.*?\|>", "", text)
    return text.strip()

# =========================================================
# 💬 CASUAL CHAT DETECTION
# =========================================================
_NON_CASUAL_PATTERN = re.compile(
    r"\b(btc|eth|sol|xau|xauusd|gold|bitcoin|ethereum|solana|crypto|forex|trade|trading|trader|signal|signals|"
    r"buy|sell|entry|stop\s*loss|take\s*profit|tp|sl|rsi|ema|atr|macd|support|resistance|breakout|chart|market|markets|"
    r"price|prices|plan|news|fed|fomc|cpi|nfp|alert|alerts|remind|reminder|notify|notification|notifications|"
    r"memory|remember|tts|voice|subscribe|subscription|premium|status|analysis|analyze|analyse|"
    r"gdelt|geopolitical|conflict|war|sanction|election|global|international|whale|narrative|sentiment)\b",
    re.IGNORECASE,
)
_NUMBER_PATTERN = re.compile(r"\b\d{3,}(?:[.,]\d+)?\b")

def _is_casual_chat(text: str, has_image: bool = False, needs_web: bool = False) -> bool:
    if has_image or needs_web:
        return False
    t = (text or "").strip()
    if not t:
        return False
    if t.startswith("/"):
        return False
    if _NON_CASUAL_PATTERN.search(t):
        return False
    if _NUMBER_PATTERN.search(t):
        return False
    return True

# =========================================================
# 🌍 GDELT 2.0 DOC API HELPERS (Free, No API Key Required)
# =========================================================

def search_gdelt_doc(
    query: str,
    mode: str = "artlist",
    max_records: int = GDELT_MAX_RECORDS,
    timespan: str = GDELT_DEFAULT_TIMESPAN,
    sort: str = "hybridrel",
) -> Dict[str, Any]:
    """
    Search the GDELT 2.0 DOC API for global news articles.
    
    Args:
        query: Search query (supports OR, phrases, operators like domain:, theme:, tone<)
        mode: Output mode - "artlist" (article list), "timelinevol" (volume timeline), 
              "timelinetone" (tone timeline), "tonechart" (tone histogram)
        max_records: Maximum records to return (max 250)
        timespan: Time span like "24h", "7d", "3m" (last 3 months max)
        sort: "hybridrel" (relevance), "datedesc" (newest first), "dateasc" (oldest first)
    
    Returns:
        {"success": bool, "articles": [...], "timeline": [...], "error": str|None}
        Never raises.
    """
    if not query or not query.strip():
        return {"success": False, "articles": [], "timeline": [], "error": "empty_query"}

    try:
        params = {
            "query": query.strip()[:500],
            "mode": mode,
            "format": "json",
            "maxrecords": min(max_records, 250),
            "timespan": timespan,
            "sort": sort,
        }
        resp = requests.get(
            GDELT_DOC_API_URL,
            params=params,
            timeout=GDELT_TIMEOUT,
            headers={"User-Agent": "KingZarryAI/1.0"},
        )
        if resp.status_code >= 400:
            return {"success": False, "articles": [], "timeline": [], "error": f"HTTP {resp.status_code}"}
        data = resp.json()

        # ArtList mode returns {"articles": [...]}
        if "articles" in data:
            articles = []
            for art in data.get("articles", [])[:max_records]:
                articles.append({
                    "title": art.get("title", "Untitled"),
                    "url": art.get("url", ""),
                    "source": art.get("domain", "unknown"),
                    "country": art.get("sourcecountry", ""),
                    "language": art.get("language", ""),
                    "seendate": art.get("seendate", ""),
                    "socialimage": art.get("socialimage", ""),
                })
            return {"success": True, "articles": articles, "timeline": [], "error": None, "mode": mode}

        # Timeline modes return {"timeline": [...]}
        if "timeline" in data:
            timeline = []
            for point in data.get("timeline", [])[:max_records]:
                timeline.append(point)
            return {"success": True, "articles": [], "timeline": timeline, "error": None, "mode": mode}

        return {"success": True, "articles": [], "timeline": [], "error": None, "mode": mode, "raw": data}

    except requests.exceptions.Timeout:
        return {"success": False, "articles": [], "timeline": [], "error": "timeout"}
    except Exception as e:
        return {"success": False, "articles": [], "timeline": [], "error": _redact_secrets(str(e))[:200]}


def format_gdelt_for_ai(gdelt_result: Dict[str, Any], max_articles: int = 5) -> str:
    """Format GDELT search results for injection into an AI prompt."""
    if not gdelt_result.get("success"):
        return ""
    articles = gdelt_result.get("articles", [])
    timeline = gdelt_result.get("timeline", [])

    if not articles and not timeline:
        return ""

    lines = ["--- GDELT GLOBAL NEWS INTELLIGENCE (65 languages, updated every 15 min) ---"]

    if articles:
        lines.append(f"Latest global coverage ({len(articles)} articles):")
        for i, art in enumerate(articles[:max_articles], 1):
            lines.append(
                f"{i}. [{art.get('title', 'Untitled')}]({art.get('url', '')}) "
                f"— {art.get('source', 'unknown')} "
                f"({art.get('country', '??')}, {art.get('language', '??')}) "
                f"| {art.get('seendate', '')[:16]}"
            )

    if timeline:
        lines.append(f"Coverage volume timeline ({len(timeline)} points):")
        for point in timeline[:5]:
            date = point.get("date", "")
            value = point.get("value", 0)
            lines.append(f"- {date}: {value}")

    lines.append("--- END GDELT INTELLIGENCE ---")
    return "\n".join(lines)


# =========================================================
# 📰 CRYPTO VISION (cryptocurrency.cv) FREE HELPERS
# =========================================================

def get_crypto_vision_intelligence() -> Dict[str, Any]:
    """
    Fetch free crypto intelligence from cryptocurrency.cv.
    Tries multiple free endpoints; returns whatever succeeds.
    No API key required for free endpoints.
    """
    base = CRYPTOVISION_BASE_URL
    intel = {
        "signals": [],
        "whales": [],
        "narratives": [],
        "sentiment": None,
        "fear_greed": None,
        "breaking": [],
        "errors": [],
    }

    headers = {"User-Agent": "KingZarryAI/1.0", "Accept": "application/json"}

    # Free endpoints (legacy, no API key)
    endpoints = [
        ("signals", "/api/signals", "signals"),
        ("whales", "/api/whale-alerts", "alerts"),
        ("narratives", "/api/narratives?period=24h&limit=5", "narratives"),
        ("sentiment", "/api/sentiment", None),
        ("fear_greed", "/api/fear-greed", None),
        ("breaking", "/api/breaking", "articles"),
    ]

    for name, path, key in endpoints:
        try:
            resp = requests.get(f"{base}{path}", headers=headers, timeout=CRYPTOVISION_TIMEOUT)
            if resp.status_code >= 400:
                intel["errors"].append(f"{name}: HTTP {resp.status_code}")
                continue
            data = resp.json()
            if key and key in data:
                intel[name] = data[key]
            elif isinstance(data, dict):
                intel[name] = data
            elif isinstance(data, list):
                intel[name] = data
        except requests.exceptions.Timeout:
            intel["errors"].append(f"{name}: timeout")
        except Exception as e:
            intel["errors"].append(f"{name}: {_redact_secrets(str(e))[:80]}")

    return intel


def format_crypto_vision_for_ai(intel: Dict[str, Any], max_items: int = 5) -> str:
    """Format cryptocurrency.cv intelligence for injection into an AI prompt."""
    if not intel:
        return ""
    has_data = any(intel.get(k) for k in ["signals", "whales", "narratives", "sentiment", "fear_greed", "breaking"])
    if not has_data:
        return ""

    lines = ["--- CRYPTO MARKET INTELLIGENCE (cryptocurrency.cv, free tier) ---"]

    signals = intel.get("signals", [])
    if signals:
        lines.append("AI Trading Signals:")
        for s in signals[:max_items]:
            if isinstance(s, dict):
                asset = s.get("asset") or s.get("symbol") or "?"
                sig = s.get("signal") or s.get("direction") or "?"
                strength = s.get("strength") or s.get("confidence") or "?"
                reason = (s.get("reason") or s.get("rationale") or "")[:100]
                lines.append(f"- {asset}: {sig} (strength {strength}) — {reason}")
            else:
                lines.append(f"- {str(s)[:120]}")

    whales = intel.get("whales", [])
    if whales:
        lines.append("Whale Alerts:")
        for w in whales[:max_items]:
            if isinstance(w, dict):
                asset = w.get("asset") or w.get("symbol") or "?"
                amount = w.get("amount") or w.get("usd_value") or "?"
                direction = w.get("direction") or w.get("type") or "?"
                exchange = w.get("exchange") or ""
                lines.append(f"- {asset}: {amount} ({direction}) {exchange}")
            else:
                lines.append(f"- {str(w)[:120]}")

    narratives = intel.get("narratives", [])
    if narratives:
        lines.append("Narrative Clusters:")
        for n in narratives[:max_items]:
            if isinstance(n, dict):
                theme = n.get("theme") or n.get("name") or "?"
                strength = n.get("strength") or n.get("score") or "?"
                count = n.get("articleCount") or n.get("count") or "?"
                lines.append(f"- {theme}: strength {strength}, {count} articles")
            else:
                lines.append(f"- {str(n)[:120]}")

    sentiment = intel.get("sentiment")
    if sentiment and isinstance(sentiment, dict):
        lines.append(f"Market Sentiment: {sentiment.get('overall') or sentiment.get('sentiment') or json.dumps(sentiment)[:200]}")

    fg = intel.get("fear_greed")
    if fg and isinstance(fg, dict):
        lines.append(f"Fear & Greed Index: {fg.get('value') or fg.get('score') or '?'} ({fg.get('classification') or fg.get('label') or ''})")

    breaking = intel.get("breaking", [])
    if breaking:
        lines.append("Breaking Crypto News:")
        for b in breaking[:max_items]:
            if isinstance(b, dict):
                title = b.get("title") or b.get("headline") or "?"
                url = b.get("url") or b.get("link") or ""
                lines.append(f"- [{title}]({url})")
            else:
                lines.append(f"- {str(b)[:120]}")

    if intel.get("errors"):
        lines.append(f"(Some endpoints unavailable: {', '.join(intel['errors'][:3])})")

    lines.append("--- END CRYPTO INTELLIGENCE ---")
    return "\n".join(lines)


# =========================================================
# 🎨 MEDIA INTENT PATTERNS (Image + Video)
# =========================================================

_IMAGE_REQUEST_PATTERNS = re.compile(
    r"\b("
    r"generate\s+(?:an?\s+)?image|create\s+(?:an?\s+)?image|make\s+(?:an?\s+)?image|"
    r"generate\s+(?:a\s+)?picture|create\s+(?:a\s+)?picture|make\s+(?:a\s+)?picture|"
    r"draw|sketch|render|visualize|illustrate|paint|"
    r"image\s+of|picture\s+of|photo\s+of|artwork\s+of|art\s+of|portrait\s+of|"
    r"edit\s+(?:this\s+|the\s+)?(?:image|photo|picture)|"
    r"modify\s+(?:this\s+|the\s+)?(?:image|photo|picture)|"
    r"change\s+(?:this\s+|the\s+)?(?:image|photo|picture)|"
    r"remove\s+background|background\s+removal|"
    r"add\s+to\s+(?:this\s+|the\s+)?(?:image|photo)|"
    r"style\s+transfer|img2img|image\s+to\s+image|"
    r"make\s+(?:this|it)\s+look|turn\s+(?:this|it)\s+into"
    r")\b",
    re.IGNORECASE,
)

_VIDEO_REQUEST_PATTERNS = re.compile(
    r"\b("
    r"generate\s+(?:a\s+)?video|create\s+(?:a\s+)?video|make\s+(?:a\s+)?video|"
    r"generate\s+(?:a\s+)?clip|create\s+(?:a\s+)?clip|make\s+(?:a\s+)?clip|"
    r"video\s+of|clip\s+of|animation\s+of|animate|"
    r"text\s+to\s+video|image\s+to\s+video|"
    r"video\s+from|make\s+me\s+a\s+video|make\s+me\s+a\s+clip"
    r")\b",
    re.IGNORECASE,
)

_MEDIA_GUARD_PATTERN = re.compile(
    r"\b(btc|eth|sol|xau|gold|bitcoin|ethereum|solana|trade|trading|signal|entry|stop\s*loss|"
    r"take\s*profit|rsi|ema|atr|support|resistance|alert|alerts|remind|notify|notification|"
    r"price|prices|market|news|gdelt|geopolitical|conflict|war|sanction|election)\b",
    re.IGNORECASE,
)

_CLEAR_GENERATION_VERB = re.compile(
    r"\b("
    r"draw|sketch|render|illustrate|paint|"
    r"generate\s+(?:an?\s+|the\s+|me\s+(?:an?\s+)?)?(?:image|picture|photo|art|artwork|video|clip|animation)|"
    r"create\s+(?:an?\s+|the\s+|me\s+(?:an?\s+)?)?(?:image|picture|photo|art|artwork|video|clip|animation)|"
    r"make\s+(?:me\s+)?(?:an?\s+)?(?:image|picture|photo|art|artwork|video|clip|animation)|"
    r"animate"
    r")\b",
    re.IGNORECASE,
)

_VIDEO_STATUS_CHECK_PATTERN = re.compile(
    r"\b(?:check|status|track|poll|is\s+it\s+ready|any\s+update)\b"
    r"[^.]{0,80}?"
    r"\b(?:video|task|clip|render|agnes|acedata)\b"
    r"[^.]{0,80}?"
    r"\b([a-zA-Z0-9][a-zA-Z0-9_\-]{5,})\b",
    re.IGNORECASE,
)

# =========================================================
# 🧠 NEWS/WEB INTENT DETECTION FOR GDELT + CRYPTO VISION
# =========================================================

_GDELT_TRIGGER_PATTERN = re.compile(
    r"\b("
    r"geopolitical|geopolitics|global\s+news|world\s+news|international\s+news|"
    r"conflict|war|invasion|military|sanction|sanctions|embargo|"
    r"election|elections|vote|referendum|coup|protest|"
    r"tension|tensions|crisis|humanitarian|refugee|"
    r"nato|united\s+nations|un\s+security|council|eu\s+summit|g7|g20|brics|"
    r"tariff|tariffs|trade\s+war|trade\s+deal|"
    r"oil\s+supply|opec|pipeline|strait|shipping\s+lane|"
    r"nuclear|missile|drone\s+strike|airstrike|"
    r"what\s+is\s+happening\s+in|latest\s+on\s+the\s+war|"
    r"news\s+about\s+the\s+conflict|global\s+coverage"
    r")\b",
    re.IGNORECASE,
)

_CRYPTOVISION_TRIGGER_PATTERN = re.compile(
    r"\b("
    r"whale\s+alert|whale\s+activity|whale\s+movement|whale\s+transaction|"
    r"crypto\s+signal|crypto\s+signals|ai\s+signal|trading\s+signal\s+for|"
    r"narrative|narratives|crypto\s+narrative|"
    r"market\s+sentiment|sentiment\s+analysis|"
    r"fear\s+and\s+greed|fear\s+&\s+greed|fear\s+greed\s+index|"
    r"anomaly|anomalies|unusual\s+activity|"
    r"breaking\s+crypto|crypto\s+news|latest\s+crypto\s+news"
    r")\b",
    re.IGNORECASE,
)


def _detect_media_intent(prompt: str, has_image: bool = False) -> Optional[Dict[str, Any]]:
    """
    Detect if the user wants image/video generation or editing.
    Returns None for normal text, or a dict describing the intent.
    """
    if not prompt:
        return None
    text = prompt.strip()
    if not text:
        return None

    has_clear_verb = bool(_CLEAR_GENERATION_VERB.search(text))
    if _MEDIA_GUARD_PATTERN.search(text) and not has_clear_verb:
        return None

    is_video = bool(_VIDEO_REQUEST_PATTERNS.search(text))
    is_image = bool(_IMAGE_REQUEST_PATTERNS.search(text))

    if is_video:
        return {
            "kind": "video",
            "mode": "image" if has_image else "text",
            "prompt": text,
            "seconds": 5,
            "size": "720P",
            "aspect_ratio": "16:9",
        }

    if is_image or (has_image and _IMAGE_REQUEST_PATTERNS.search(text)):
        return {
            "kind": "image_edit" if has_image else "image",
            "mode": "image-to-image" if has_image else "text-to-image",
            "prompt": text,
            "size": "1024x1024",
        }

    return None


def _should_use_gdelt(prompt: str) -> bool:
    """True if the prompt asks for global/geopolitical/international news."""
    if not prompt:
        return False
    return bool(_GDELT_TRIGGER_PATTERN.search(prompt))


def _should_use_cryptovision(prompt: str) -> bool:
    """True if the prompt asks for crypto intelligence (whales, signals, narratives)."""
    if not prompt:
        return False
    return bool(_CRYPTOVISION_TRIGGER_PATTERN.search(prompt))


# =========================================================
# 🎨 AGNES AI MEDIA ENGINE
# =========================================================

def _agnes_headers() -> Dict[str, str]:
    return {
        "Authorization": f"Bearer {AGNES_API_KEY}",
        "Content-Type": "application/json",
    }


def agnes_generate_image(prompt: str, size: str = "1024x1024", max_retries: int = 2) -> Dict[str, Any]:
    if not AGNES_API_KEY:
        return {"success": False, "url": None, "error": "agnes_not_configured", "model": AGNES_IMAGE_MODEL}
    url = f"{AGNES_BASE_URL}/images/generations"
    payload = {"model": AGNES_IMAGE_MODEL, "prompt": prompt, "size": size}
    last_error = None
    for attempt in range(max_retries + 1):
        try:
            resp = requests.post(url, headers=_agnes_headers(), json=payload, timeout=AGNES_IMAGE_TIMEOUT)
            if resp.status_code == 429:
                last_error = "rate_limit"
                if attempt < max_retries:
                    time.sleep(1.5 * (attempt + 1))
                    continue
                return {"success": False, "url": None, "error": "rate_limit", "model": AGNES_IMAGE_MODEL}
            if resp.status_code >= 400:
                last_error = _redact_secrets(resp.text[:300])
                if resp.status_code in (500, 502, 503, 504) and attempt < max_retries:
                    time.sleep(1.2 * (attempt + 1))
                    continue
                return {"success": False, "url": None, "error": last_error, "model": AGNES_IMAGE_MODEL}
            data = resp.json()
            items = data.get("data") or []
            if not items:
                return {"success": False, "url": None, "error": "empty_response", "model": AGNES_IMAGE_MODEL}
            first = items[0]
            return {
                "success": True,
                "url": first.get("url") or first.get("b64_json"),
                "revised_prompt": first.get("revised_prompt"),
                "error": None,
                "model": AGNES_IMAGE_MODEL,
            }
        except requests.exceptions.Timeout:
            last_error = "timeout"
            if attempt < max_retries:
                time.sleep(1.5 * (attempt + 1))
                continue
        except Exception as e:
            last_error = _redact_secrets(str(e))
    return {"success": False, "url": None, "error": last_error or "unknown_error", "model": AGNES_IMAGE_MODEL}


def agnes_edit_image(prompt: str, image_url: str, size: str = "1024x1024", max_retries: int = 2) -> Dict[str, Any]:
    if not AGNES_API_KEY:
        return {"success": False, "url": None, "error": "agnes_not_configured", "model": AGNES_IMAGE_MODEL}
    if not image_url:
        return {"success": False, "url": None, "error": "missing_image_url", "model": AGNES_IMAGE_MODEL}
    url = f"{AGNES_BASE_URL}/images/generations"
    payload = {
        "model": AGNES_IMAGE_MODEL,
        "prompt": prompt,
        "size": size,
        "extra_body": {"image": [image_url], "response_format": "url"},
    }
    last_error = None
    for attempt in range(max_retries + 1):
        try:
            resp = requests.post(url, headers=_agnes_headers(), json=payload, timeout=AGNES_IMAGE_TIMEOUT)
            if resp.status_code == 429:
                last_error = "rate_limit"
                if attempt < max_retries:
                    time.sleep(1.5 * (attempt + 1))
                    continue
                return {"success": False, "url": None, "error": "rate_limit", "model": AGNES_IMAGE_MODEL}
            if resp.status_code >= 400:
                last_error = _redact_secrets(resp.text[:300])
                if resp.status_code in (500, 502, 503, 504) and attempt < max_retries:
                    time.sleep(1.2 * (attempt + 1))
                    continue
                return {"success": False, "url": None, "error": last_error, "model": AGNES_IMAGE_MODEL}
            data = resp.json()
            items = data.get("data") or []
            if not items:
                return {"success": False, "url": None, "error": "empty_response", "model": AGNES_IMAGE_MODEL}
            first = items[0]
            return {
                "success": True,
                "url": first.get("url") or first.get("b64_json"),
                "revised_prompt": first.get("revised_prompt"),
                "error": None,
                "model": AGNES_IMAGE_MODEL,
            }
        except requests.exceptions.Timeout:
            last_error = "timeout"
            if attempt < max_retries:
                time.sleep(1.5 * (attempt + 1))
                continue
        except Exception as e:
            last_error = _redact_secrets(str(e))
    return {"success": False, "url": None, "error": last_error or "unknown_error", "model": AGNES_IMAGE_MODEL}


def agnes_create_video(prompt: str, seconds: int = 5, size: str = "720P", aspect_ratio: str = "16:9", mode: str = "text") -> Dict[str, Any]:
    if not AGNES_API_KEY:
        return {"success": False, "video_id": None, "error": "agnes_not_configured", "model": AGNES_VIDEO_MODEL}
    url = f"{AGNES_BASE_URL}/videos"
    payload = {
        "model": AGNES_VIDEO_MODEL,
        "prompt": prompt,
        "seconds": str(seconds),
        "mode": mode,
        "size": size,
        "aspect_ratio": aspect_ratio,
    }
    try:
        resp = requests.post(url, headers=_agnes_headers(), json=payload, timeout=45)
        if resp.status_code >= 400:
            return {"success": False, "video_id": None, "error": _redact_secrets(resp.text[:300]), "model": AGNES_VIDEO_MODEL}
        data = resp.json()
        video_id = data.get("video_id") or data.get("id") or data.get("task_id")
        if not video_id:
            return {"success": False, "video_id": None, "error": "no_task_id_in_response", "model": AGNES_VIDEO_MODEL}
        return {"success": True, "video_id": str(video_id), "status": data.get("status", "queued"), "error": None, "model": AGNES_VIDEO_MODEL}
    except requests.exceptions.Timeout:
        return {"success": False, "video_id": None, "error": "timeout", "model": AGNES_VIDEO_MODEL}
    except Exception as e:
        return {"success": False, "video_id": None, "error": _redact_secrets(str(e)), "model": AGNES_VIDEO_MODEL}


def agnes_poll_video(video_id: str, max_wait: Optional[int] = None) -> Dict[str, Any]:
    if not AGNES_API_KEY:
        return {"success": False, "status": "error", "error": "agnes_not_configured"}
    if not video_id:
        return {"success": False, "status": "error", "error": "missing_video_id"}
    if max_wait is None:
        max_wait = AGNES_VIDEO_POLL_TIMEOUT
    poll_url = f"{AGNES_BASE_URL}/videos/{video_id}"
    start = time.time()
    last_status = "queued"
    while time.time() - start < max_wait:
        try:
            resp = requests.get(poll_url, headers=_agnes_headers(), timeout=30)
            if resp.status_code >= 400:
                return {"success": False, "status": "error", "error": _redact_secrets(resp.text[:300]), "video_id": video_id}
            data = resp.json()
            status = str(data.get("status", "")).lower()
            last_status = status or last_status
            if status in ("completed", "succeeded", "success", "done"):
                url = (data.get("url") or data.get("video_url") or (data.get("metadata") or {}).get("url") or (data.get("output") or {}).get("url"))
                return {"success": True, "status": "completed", "url": url, "video_id": video_id}
            if status in ("failed", "error", "cancelled", "canceled"):
                return {"success": False, "status": "failed", "error": data.get("error") or data.get("message") or "task_failed", "video_id": video_id}
        except requests.exceptions.Timeout:
            pass
        except Exception:
            pass
        time.sleep(AGNES_VIDEO_POLL_INTERVAL)
    return {"success": False, "status": "timeout", "error": "poll_timeout", "video_id": video_id, "last_status": last_status}


# =========================================================
# 🟣 ACEDATA CLOUD MEDIA ENGINE (Fallback)
# =========================================================

def _acedata_headers() -> Dict[str, str]:
    return {"Authorization": f"Bearer {ACEDATA_API_KEY}", "Accept": "application/json", "Content-Type": "application/json"}


def _acedata_extract_task_id(data: Dict[str, Any]) -> Optional[str]:
    if not isinstance(data, dict):
        return None
    tid = data.get("task_id") or data.get("id")
    if tid:
        return str(tid)
    items = data.get("data")
    if isinstance(items, list) and items:
        first = items[0]
        if isinstance(first, dict):
            tid = first.get("task_id") or first.get("id")
            if tid:
                return str(tid)
    return None


def _acedata_extract_media_url(data: Dict[str, Any], url_keys: Tuple[str, ...]) -> Tuple[Optional[str], Optional[str]]:
    if not isinstance(data, dict):
        return None, None
    items = data.get("data")
    candidates = []
    if isinstance(items, list) and items:
        candidates.extend([i for i in items if isinstance(i, dict)])
    candidates.append(data)
    for item in candidates:
        state = str(item.get("state") or item.get("status") or "").lower()
        for key in url_keys:
            val = item.get(key)
            if val:
                return val, state
        if state:
            return None, state
    return None, None


def acedata_generate_image(prompt: str, width: int = 1024, height: int = 1024, count: int = 1) -> Dict[str, Any]:
    if not ACEDATA_API_KEY:
        return {"success": False, "url": None, "error": "acedata_not_configured", "model": ACEDATA_IMAGE_MODEL}
    submit_url = f"{ACEDATA_BASE_URL}{ACEDATA_IMAGE_SUBMIT_PATH}"
    payload = {"model": ACEDATA_IMAGE_MODEL, "prompt": prompt, "width": width, "height": height, "count": count}
    try:
        resp = requests.post(submit_url, headers=_acedata_headers(), json=payload, timeout=ACEDATA_IMAGE_TIMEOUT)
        if resp.status_code == 429:
            return {"success": False, "url": None, "error": "rate_limit", "model": ACEDATA_IMAGE_MODEL}
        if resp.status_code >= 400:
            return {"success": False, "url": None, "error": _redact_secrets(resp.text[:300]), "model": ACEDATA_IMAGE_MODEL}
        data = resp.json()
    except requests.exceptions.Timeout:
        return {"success": False, "url": None, "error": "timeout", "model": ACEDATA_IMAGE_MODEL}
    except Exception as e:
        return {"success": False, "url": None, "error": _redact_secrets(str(e)), "model": ACEDATA_IMAGE_MODEL}

    url_keys = ("image_url", "url", "output_url")
    media_url, state = _acedata_extract_media_url(data, url_keys)
    if media_url:
        return {"success": True, "url": media_url, "error": None, "model": ACEDATA_IMAGE_MODEL, "provider": "acedata"}

    task_id = _acedata_extract_task_id(data)
    if not task_id:
        return {"success": False, "url": None, "error": "no_task_id_in_response", "model": ACEDATA_IMAGE_MODEL}

    tasks_url = f"{ACEDATA_BASE_URL}{ACEDATA_IMAGE_TASKS_PATH}"
    start = time.time()
    while time.time() - start < ACEDATA_IMAGE_POLL_TIMEOUT:
        try:
            poll_resp = requests.get(tasks_url, headers=_acedata_headers(), params={"task_id": task_id}, timeout=30)
            if poll_resp.status_code >= 400:
                return {"success": False, "url": None, "error": _redact_secrets(poll_resp.text[:300]), "model": ACEDATA_IMAGE_MODEL}
            poll_data = poll_resp.json()
            media_url, state = _acedata_extract_media_url(poll_data, url_keys)
            if media_url:
                return {"success": True, "url": media_url, "error": None, "model": ACEDATA_IMAGE_MODEL, "provider": "acedata"}
            if state in ("failed", "error"):
                return {"success": False, "url": None, "error": "task_failed", "model": ACEDATA_IMAGE_MODEL}
        except requests.exceptions.Timeout:
            pass
        except Exception:
            pass
        time.sleep(ACEDATA_IMAGE_POLL_INTERVAL)
    return {"success": False, "url": None, "error": "poll_timeout", "model": ACEDATA_IMAGE_MODEL, "task_id": task_id}


def acedata_edit_image(prompt: str, image_url: str, width: int = 1024, height: int = 1024) -> Dict[str, Any]:
    if not ACEDATA_API_KEY:
        return {"success": False, "url": None, "error": "acedata_not_configured", "model": ACEDATA_IMAGE_MODEL}
    if not image_url:
        return {"success": False, "url": None, "error": "missing_image_url", "model": ACEDATA_IMAGE_MODEL}
    submit_url = f"{ACEDATA_BASE_URL}{ACEDATA_IMAGE_SUBMIT_PATH}"
    payload = {"model": ACEDATA_IMAGE_MODEL, "prompt": prompt, "width": width, "height": height, "count": 1, "image_url": image_url}
    try:
        resp = requests.post(submit_url, headers=_acedata_headers(), json=payload, timeout=ACEDATA_IMAGE_TIMEOUT)
        if resp.status_code == 429:
            return {"success": False, "url": None, "error": "rate_limit", "model": ACEDATA_IMAGE_MODEL}
        if resp.status_code >= 400:
            return {"success": False, "url": None, "error": _redact_secrets(resp.text[:300]), "model": ACEDATA_IMAGE_MODEL}
        data = resp.json()
    except requests.exceptions.Timeout:
        return {"success": False, "url": None, "error": "timeout", "model": ACEDATA_IMAGE_MODEL}
    except Exception as e:
        return {"success": False, "url": None, "error": _redact_secrets(str(e)), "model": ACEDATA_IMAGE_MODEL}

    url_keys = ("image_url", "url", "output_url")
    media_url, state = _acedata_extract_media_url(data, url_keys)
    if media_url:
        return {"success": True, "url": media_url, "error": None, "model": ACEDATA_IMAGE_MODEL, "provider": "acedata"}

    task_id = _acedata_extract_task_id(data)
    if not task_id:
        return {"success": False, "url": None, "error": "no_task_id_in_response", "model": ACEDATA_IMAGE_MODEL}

    tasks_url = f"{ACEDATA_BASE_URL}{ACEDATA_IMAGE_TASKS_PATH}"
    start = time.time()
    while time.time() - start < ACEDATA_IMAGE_POLL_TIMEOUT:
        try:
            poll_resp = requests.get(tasks_url, headers=_acedata_headers(), params={"task_id": task_id}, timeout=30)
            if poll_resp.status_code >= 400:
                return {"success": False, "url": None, "error": _redact_secrets(poll_resp.text[:300]), "model": ACEDATA_IMAGE_MODEL}
            poll_data = poll_resp.json()
            media_url, state = _acedata_extract_media_url(poll_data, url_keys)
            if media_url:
                return {"success": True, "url": media_url, "error": None, "model": ACEDATA_IMAGE_MODEL, "provider": "acedata"}
            if state in ("failed", "error"):
                return {"success": False, "url": None, "error": "task_failed", "model": ACEDATA_IMAGE_MODEL}
        except requests.exceptions.Timeout:
            pass
        except Exception:
            pass
        time.sleep(ACEDATA_IMAGE_POLL_INTERVAL)
    return {"success": False, "url": None, "error": "poll_timeout", "model": ACEDATA_IMAGE_MODEL, "task_id": task_id}


def acedata_create_video(prompt: str, aspect_ratio: str = "16:9", image_url: Optional[str] = None) -> Dict[str, Any]:
    if not ACEDATA_API_KEY:
        return {"success": False, "video_id": None, "url": None, "error": "acedata_not_configured", "model": ACEDATA_VIDEO_MODEL}
    submit_url = f"{ACEDATA_BASE_URL}{ACEDATA_VIDEO_SUBMIT_PATH}"
    action = "image2video" if image_url else "text2video"
    payload = {"action": action, "model": ACEDATA_VIDEO_MODEL, "prompt": prompt, "aspect_ratio": aspect_ratio}
    if image_url:
        payload["image_url"] = image_url
    try:
        resp = requests.post(submit_url, headers=_acedata_headers(), json=payload, timeout=ACEDATA_VIDEO_TIMEOUT)
        if resp.status_code == 429:
            return {"success": False, "video_id": None, "url": None, "error": "rate_limit", "model": ACEDATA_VIDEO_MODEL}
        if resp.status_code >= 400:
            return {"success": False, "video_id": None, "url": None, "error": _redact_secrets(resp.text[:300]), "model": ACEDATA_VIDEO_MODEL}
        data = resp.json()
    except requests.exceptions.Timeout:
        return {"success": False, "video_id": None, "url": None, "error": "timeout", "model": ACEDATA_VIDEO_MODEL}
    except Exception as e:
        return {"success": False, "video_id": None, "url": None, "error": _redact_secrets(str(e)), "model": ACEDATA_VIDEO_MODEL}

    url_keys = ("video_url", "url", "output_url")
    media_url, state = _acedata_extract_media_url(data, url_keys)
    if media_url and state in ("succeeded", "completed", "success", "done", ""):
        return {"success": True, "video_id": _acedata_extract_task_id(data), "url": media_url, "error": None, "model": ACEDATA_VIDEO_MODEL, "provider": "acedata"}
    if state in ("failed", "error"):
        return {"success": False, "video_id": None, "url": None, "error": "task_failed", "model": ACEDATA_VIDEO_MODEL}

    task_id = _acedata_extract_task_id(data)
    if not task_id:
        return {"success": False, "video_id": None, "url": None, "error": "no_task_id_in_response", "model": ACEDATA_VIDEO_MODEL}
    return {"success": True, "video_id": task_id, "url": None, "status": state or "queued", "error": None, "model": ACEDATA_VIDEO_MODEL, "provider": "acedata"}


def acedata_poll_video(video_id: str, max_wait: Optional[int] = None) -> Dict[str, Any]:
    if not ACEDATA_API_KEY:
        return {"success": False, "status": "error", "error": "acedata_not_configured"}
    if not video_id:
        return {"success": False, "status": "error", "error": "missing_video_id"}
    if max_wait is None:
        max_wait = ACEDATA_VIDEO_POLL_TIMEOUT
    tasks_url = f"{ACEDATA_BASE_URL}{ACEDATA_VIDEO_TASKS_PATH}"
    url_keys = ("video_url", "url", "output_url")
    start = time.time()
    last_status = "queued"
    while time.time() - start < max_wait:
        try:
            resp = requests.get(tasks_url, headers=_acedata_headers(), params={"task_id": video_id}, timeout=30)
            if resp.status_code >= 400:
                return {"success": False, "status": "error", "error": _redact_secrets(resp.text[:300]), "video_id": video_id}
            data = resp.json()
            media_url, state = _acedata_extract_media_url(data, url_keys)
            last_status = state or last_status
            if media_url:
                return {"success": True, "status": "completed", "url": media_url, "video_id": video_id}
            if state in ("failed", "error", "cancelled", "canceled"):
                return {"success": False, "status": "failed", "error": "task_failed", "video_id": video_id}
        except requests.exceptions.Timeout:
            pass
        except Exception:
            pass
        time.sleep(ACEDATA_VIDEO_POLL_INTERVAL)
    return {"success": False, "status": "timeout", "error": "poll_timeout", "video_id": video_id, "last_status": last_status}


# =========================================================
# 🔒 SAFE TOOL EXECUTION LAYER
# =========================================================
TOOL_MARKUP_PATTERN = re.compile(r"<tool_call>.*?</tool_call>", re.DOTALL | re.IGNORECASE)
TOOL_MARKUP_START_PATTERN = re.compile(r"<tool_call>|</tool_call>|<function_calls>|</function_calls>", re.IGNORECASE)
SQLITE_TOOL_PATTERN = re.compile(r"<tool_call>\s*sqlite3.*?</tool_call>", re.DOTALL | re.IGNORECASE)
RAW_SQL_PATTERN = re.compile(r"SELECT\s+.*FROM\s+price_alerts.*", re.IGNORECASE | re.DOTALL)
DB_PATH_PATTERN = re.compile(r"king_zarry.*\.db", re.IGNORECASE)
TOOL_TAG_PATTERN = re.compile(r"</?\s*(?:tool_call|function_calls|invoke|parameter)\b[^>]*>", re.IGNORECASE)

ALLOWED_TOOLS = {"get_user_alert_status"}

def _detect_tool_requests(text: str):
    if not text:
        return []
    found = []
    safe_matches = re.findall(r"<tool_call>\s*(get_user_alert_status)\s*</tool_call>", text, re.IGNORECASE)
    for m in safe_matches:
        found.append(m.lower())
    return found

def _detect_forbidden_tool_attempts(text: str) -> bool:
    if not text:
        return False
    low = text.lower()
    if "sqlite3" in low and "<tool_call>" in low:
        return True
    if "<tool_call>" in low and ("select" in low and "from price_alerts" in low):
        return True
    if SQLITE_TOOL_PATTERN.search(text):
        return True
    if re.search(r"<tool_call>\s*sqlite3", text, re.IGNORECASE):
        return True
    return False

def _sanitize_final_response(text: str) -> str:
    if not text:
        return ""
    text = TOOL_MARKUP_PATTERN.sub("", text)
    text = TOOL_MARKUP_START_PATTERN.sub("", text)
    text = RAW_SQL_PATTERN.sub("", text)
    text = DB_PATH_PATTERN.sub("", text)
    text = TOOL_TAG_PATTERN.sub("", text)
    return text.strip()

def _execute_safe_tool(tool_name: str, authenticated_user_id: str):
    logger.info(f"Tool request detected: {tool_name}")
    try:
        if tool_name.lower() == "get_user_alert_status":
            try:
                from price_alerts import get_user_alert_status
            except Exception as e:
                logger.warning(f"get_user_alert_status unavailable: {_redact_secrets(str(e))}")
                return {"success": False, "error": "tool_not_implemented"}
            try:
                uid_int = int(str(authenticated_user_id))
                result = get_user_alert_status(uid_int)
            except ValueError:
                result = get_user_alert_status(authenticated_user_id)
            logger.info(f"Tool execution successful: {tool_name}")
            return result
        else:
            logger.warning(f"Tool blocked - unknown: {tool_name}")
            return {"success": False, "error": "unknown_tool"}
    except Exception as e:
        logger.error(f"Tool execution failed: {_redact_secrets(str(e))}")
        return {"success": False, "error": "execution_failed"}

# =========================================================
# 🔒 STRICT MARKET VALIDATION LAYER
# =========================================================
MTF_WEIGHTS = {"4h": 0.35, "1h": 0.30, "15m": 0.25, "5m": 0.10}

def _safe_float(v, default=None):
    try:
        if v is None:
            return default
        fv = float(v)
        if math.isnan(fv) or math.isinf(fv):
            return default
        return fv
    except Exception:
        return default

def _is_valid_number(v):
    if v is None:
        return False
    try:
        fv = float(v)
        if math.isnan(fv) or math.isinf(fv):
            return False
        return True
    except Exception:
        return False

def _is_valid_price(v):
    fv = _safe_float(v)
    if fv is None:
        return False
    if fv <= 0:
        return False
    if math.isnan(fv) or math.isinf(fv):
        return False
    return True

def validate_data_integrity(market: Dict[str, Any]) -> Tuple[bool, str]:
    if not market:
        return False, "Market data is empty"
    price = market.get("price") or market.get("current_price")
    if not _is_valid_price(price):
        return False, f"Invalid price: {price}"
    atr = market.get("atr")
    if atr is not None:
        fv = _safe_float(atr)
        if fv is None or fv <= 0 or math.isnan(fv) or math.isinf(fv):
            return False, f"Invalid ATR: {atr}"
    for key in ["ema9", "ema21", "ema50"]:
        if key in market and market[key] is not None:
            fv = _safe_float(market[key])
            if fv is None or fv <= 0:
                return False, f"Invalid {key}: {market[key]}"
    direction = (market.get("direction") or market.get("signal") or "WAIT").upper()
    if direction in ("BUY", "SELL"):
        el = market.get("entry_low")
        eh = market.get("entry_high")
        sl = market.get("stop_loss")
        if not _is_valid_price(el) or not _is_valid_price(eh):
            return False, f"Invalid entry zone: {el}-{eh}"
        if not _is_valid_price(sl):
            return False, f"Invalid stop_loss: {sl}"
        for tp_key in ["tp1", "tp2", "tp3"]:
            tp = market.get(tp_key)
            if tp is not None and not _is_valid_price(tp):
                return False, f"Invalid {tp_key}: {tp}"
    return True, ""

def validate_ema_alignment_raw(market: Dict[str, Any]) -> Dict[str, Any]:
    ema9 = _safe_float(market.get("ema9"))
    ema21 = _safe_float(market.get("ema21"))
    ema50 = _safe_float(market.get("ema50"))
    price = _safe_float(market.get("price") or market.get("current_price"))
    if None in (ema9, ema21, ema50, price) or price <= 0:
        return {"alignment": "UNKNOWN", "bullish": False, "bearish": False, "flat": False, "separation_pct": 0, "reason": "Missing EMA data"}
    atr = _safe_float(market.get("atr"), 0)
    price_threshold = price * 0.0008
    if atr and atr > 0:
        threshold = max(price_threshold, atr * 0.15)
    else:
        threshold = price_threshold
    diff_9_21 = abs(ema9 - ema21)
    diff_21_50 = abs(ema21 - ema50)
    diff_9_50 = abs(ema9 - ema50)
    if diff_9_21 < threshold and diff_21_50 < threshold and diff_9_50 < threshold:
        return {"alignment": "FLAT", "bullish": False, "bearish": False, "flat": True, "separation_pct": (diff_9_50 / price * 100) if price else 0, "reason": f"EMA FLAT / NO CLEAR ALIGNMENT (EMA9 {ema9:.4f} ≈ EMA21 {ema21:.4f} ≈ EMA50 {ema50:.4f}, spread {diff_9_50/price*100:.3f}% < threshold)"}
    if ema9 > ema21 and ema21 > ema50:
        if diff_9_21 >= threshold * 0.3 and diff_21_50 >= threshold * 0.3:
            return {"alignment": "BULLISH_ALIGNED", "bullish": True, "bearish": False, "flat": False, "separation_pct": (diff_9_50 / price * 100), "reason": f"Bullish EMA alignment confirmed: EMA9 {ema9:.4f} > EMA21 {ema21:.4f} > EMA50 {ema50:.4f} (spread {diff_9_50/price*100:.3f}%)"}
        else:
            return {"alignment": "BULLISH_WEAK", "bullish": False, "bearish": False, "flat": False, "separation_pct": (diff_9_50 / price * 100), "reason": f"EMA bullish order but separation too small ({diff_9_50/price*100:.3f}%) - not counted as strong alignment, EMA crossover not confirmed"}
    if ema9 < ema21 and ema21 < ema50:
        if diff_9_21 >= threshold * 0.3 and diff_21_50 >= threshold * 0.3:
            return {"alignment": "BEARISH_ALIGNED", "bullish": False, "bearish": True, "flat": False, "separation_pct": (diff_9_50 / price * 100), "reason": f"Bearish EMA alignment confirmed: EMA9 {ema9:.4f} < EMA21 {ema21:.4f} < EMA50 {ema50:.4f} (spread {abs(diff_9_50)/price*100:.3f}%)"}
        else:
            return {"alignment": "BEARISH_WEAK", "bullish": False, "bearish": False, "flat": False, "separation_pct": (abs(diff_9_50) / price * 100), "reason": f"EMA bearish order but separation too small ({abs(diff_9_50)/price*100:.3f}%) - EMA crossover not confirmed"}
    return {"alignment": "MIXED", "bullish": False, "bearish": False, "flat": False, "separation_pct": (diff_9_50 / price * 100), "reason": f"EMA mixed alignment: EMA9 {ema9:.4f}, EMA21 {ema21:.4f}, EMA50 {ema50:.4f} - no clear trend"}

def detect_countertrend(market: Dict[str, Any]) -> Dict[str, Any]:
    direction = (market.get("direction") or market.get("signal") or "WAIT").upper()
    h4 = (market.get("h4_trend") or "").upper()
    h1 = (market.get("h1_trend") or "").upper()
    if direction not in ("BUY", "SELL"):
        return {"is_countertrend": False, "type": "NONE", "penalty": 0, "reason": "No directional trade"}
    is_ct = False
    penalty = 0
    reasons = []
    if direction == "BUY" and h4 == "BEARISH":
        is_ct = True
        penalty += 25
        reasons.append(f"4H BEARISH vs BUY - countertrend")
        if h1 == "BEARISH":
            penalty += 10
            reasons.append("1H also BEARISH - strong countertrend, double HTF disagreement")
    elif direction == "SELL" and h4 == "BULLISH":
        is_ct = True
        penalty += 25
        reasons.append(f"4H BULLISH vs SELL - countertrend")
        if h1 == "BULLISH":
            penalty += 10
            reasons.append("1H also BULLISH - strong countertrend, double HTF disagreement")
    elif direction == "BUY" and h1 == "BEARISH" and h4 != "BULLISH":
        is_ct = True
        penalty += 12
        reasons.append("1H BEARISH vs BUY - partial countertrend")
    elif direction == "SELL" and h1 == "BULLISH" and h4 != "BEARISH":
        is_ct = True
        penalty += 12
        reasons.append("1H BULLISH vs SELL - partial countertrend")
    return {"is_countertrend": is_ct, "type": "COUNTERTREND BUY" if is_ct and direction == "BUY" else "COUNTERTREND SELL" if is_ct else "WITH_TREND", "penalty": penalty, "reason": "; ".join(reasons) if reasons else "With-trend: HTF aligns"}

def calculate_sr_proximity(market: Dict[str, Any]) -> Dict[str, Any]:
    price = _safe_float(market.get("price") or market.get("current_price"))
    support = _safe_float(market.get("support") or market.get("nearest_support") or market.get("major_support"))
    resistance = _safe_float(market.get("resistance") or market.get("nearest_resistance") or market.get("major_resistance"))
    direction = (market.get("direction") or market.get("signal") or "WAIT").upper()
    atr = _safe_float(market.get("atr"))
    if price is None or price <= 0:
        return {"distance_to_support_pct": None, "distance_to_resistance_pct": None, "penalty": 0, "flags": [], "reason": "Invalid price for SR check"}
    dist_sup_pct = None
    dist_res_pct = None
    if support and support > 0:
        dist_sup_pct = (price - support) / price * 100 if price != 0 else None
    if resistance and resistance > 0:
        dist_res_pct = (resistance - price) / price * 100 if price != 0 else None
    penalty = 0
    flags = []
    reasons = []
    if direction == "BUY":
        if dist_res_pct is not None:
            if dist_res_pct < 0.15:
                penalty += 25
                flags.append("RESISTANCE_BREAK_REQUIRED")
                reasons.append(f"Price extremely close to resistance ({dist_res_pct:.3f}% away) - almost no upside room, RESISTANCE BREAK REQUIRED")
            elif dist_res_pct < 0.35:
                penalty += 15
                flags.append("CLOSE_TO_RESISTANCE")
                reasons.append(f"Price close to resistance ({dist_res_pct:.3f}% away) - limited upside room")
            elif dist_res_pct < 0.7:
                penalty += 7
                reasons.append(f"Price moderately close to resistance ({dist_res_pct:.3f}% away)")
        tp1 = _safe_float(market.get("tp1"))
        if tp1 and resistance and tp1 > resistance * 1.001:
            flags.append("TP1_BEYOND_RESISTANCE")
            reasons.append(f"TP1 {tp1} beyond resistance {resistance} - RESISTANCE BREAK REQUIRED for full target")
            penalty += 8
    elif direction == "SELL":
        if dist_sup_pct is not None:
            if dist_sup_pct < 0.15:
                penalty += 25
                flags.append("SUPPORT_BREAK_REQUIRED")
                reasons.append(f"Price extremely close to support ({dist_sup_pct:.3f}% away) - almost no downside room, SUPPORT BREAK REQUIRED")
            elif dist_sup_pct < 0.35:
                penalty += 15
                flags.append("CLOSE_TO_SUPPORT")
                reasons.append(f"Price close to support ({dist_sup_pct:.3f}% away) - limited downside room")
            elif dist_sup_pct < 0.7:
                penalty += 7
                reasons.append(f"Price moderately close to support ({dist_sup_pct:.3f}% away)")
        tp1 = _safe_float(market.get("tp1"))
        if tp1 and support and tp1 < support * 0.999:
            flags.append("TP1_BEYOND_SUPPORT")
            reasons.append(f"TP1 {tp1} beyond support {support} - SUPPORT BREAK REQUIRED")
            penalty += 8
    return {"distance_to_support_pct": dist_sup_pct, "distance_to_resistance_pct": dist_res_pct, "penalty": penalty, "flags": flags, "reason": "; ".join(reasons) if reasons else "SR proximity acceptable"}

def calculate_entry_status_strict(market: Dict[str, Any]) -> Dict[str, Any]:
    direction = (market.get("direction") or market.get("signal") or "WAIT").upper()
    entry_low = _safe_float(market.get("entry_low"))
    entry_high = _safe_float(market.get("entry_high"))
    current_price = _safe_float(market.get("price") or market.get("current_price") or market.get("fresh_price"))
    atr = _safe_float(market.get("atr"))
    if direction not in ("BUY", "SELL"):
        return {"status": "NO_TRADE", "label": "NO TRADE", "missed": False, "late": False, "reason": "No directional trade - WAIT"}
    if None in (entry_low, entry_high, current_price):
        return {"status": "UNKNOWN", "label": "UNKNOWN", "missed": False, "late": False, "reason": "Missing entry zone or current price - cannot determine entry status"}
    low = min(entry_low, entry_high)
    high = max(entry_low, entry_high)
    entry_mid = (low + high) / 2
    if direction == "BUY":
        if low <= current_price <= high:
            zone_size = high - low
            if zone_size > 0:
                position_pct = (current_price - low) / zone_size
                if position_pct >= 0.85:
                    return {"status": "GOOD_ENTRY", "label": "GOOD ENTRY - UPPER EDGE", "missed": False, "late": False, "reason": f"Price {current_price} at upper edge of entry zone {low}-{high} ({position_pct*100:.0f}% through zone) - still valid but not EARLY"}
                elif position_pct >= 0.4:
                    return {"status": "GOOD_ENTRY", "label": "GOOD ENTRY", "missed": False, "late": False, "reason": f"Price {current_price} inside entry zone {low}-{high} - good entry window"}
                else:
                    return {"status": "EARLY", "label": "EARLY", "missed": False, "late": False, "reason": f"Price {current_price} in lower part of entry zone {low}-{high} - early entry opportunity"}
            else:
                return {"status": "GOOD_ENTRY", "label": "GOOD ENTRY", "missed": False, "late": False, "reason": f"Price {current_price} inside entry zone"}
        if current_price > high:
            distance_atr = (current_price - high) / atr if atr and atr > 0 else (current_price - high) / current_price * 100
            if atr and atr > 0:
                if distance_atr > 2.5:
                    return {"status": "MISSED", "label": "ENTRY MISSED", "missed": True, "late": False, "reason": f"Price {current_price} moved beyond entry zone {low}-{high} by {distance_atr:.1f} ATR - ENTRY MISSED, original zone preserved, do not chase"}
                elif distance_atr > 1.0:
                    return {"status": "LATE", "label": "LATE", "missed": False, "late": True, "reason": f"Price {current_price} above entry zone {low}-{high} by {distance_atr:.1f} ATR - LATE entry, reduced edge"}
                else:
                    return {"status": "LATE", "label": "LATE - JUST ABOVE ZONE", "missed": False, "late": True, "reason": f"Price {current_price} just above entry zone {low}-{high} - late but still near"}
            else:
                pct = (current_price - high) / high * 100 if high != 0 else 0
                if pct > 0.8:
                    return {"status": "MISSED", "label": "ENTRY MISSED", "missed": True, "late": False, "reason": f"Price moved {pct:.2f}% beyond entry - ENTRY MISSED"}
                else:
                    return {"status": "LATE", "label": "LATE", "missed": False, "late": True, "reason": f"Price {pct:.2f}% above entry zone - late"}
        if current_price < low:
            distance_atr = (low - current_price) / atr if atr and atr > 0 else 0
            return {"status": "EARLY", "label": "WAITING FOR PULLBACK", "missed": False, "late": False, "reason": f"Price {current_price} below entry zone {low}-{high}, waiting for pullback into zone - EARLY stage"}
    else:
        if low <= current_price <= high:
            zone_size = high - low
            if zone_size > 0:
                position_pct = (high - current_price) / zone_size
                lower_position = (current_price - low) / zone_size
                if lower_position <= 0.15:
                    return {"status": "GOOD_ENTRY", "label": "GOOD ENTRY - LOWER EDGE", "missed": False, "late": False, "reason": f"Price {current_price} at lower edge of SELL zone {low}-{high} - still valid but not early"}
                else:
                    return {"status": "GOOD_ENTRY", "label": "GOOD ENTRY", "missed": False, "late": False, "reason": f"Price {current_price} inside SELL entry zone {low}-{high} - good entry window"}
            else:
                return {"status": "GOOD_ENTRY", "label": "GOOD ENTRY", "missed": False, "late": False, "reason": f"Price inside SELL zone"}
        if current_price < low:
            distance_atr = (low - current_price) / atr if atr and atr > 0 else 0
            if atr and atr > 0:
                if distance_atr > 2.5:
                    return {"status": "MISSED", "label": "ENTRY MISSED", "missed": True, "late": False, "reason": f"Price {current_price} moved below SELL zone {low}-{high} by {distance_atr:.1f} ATR - ENTRY MISSED"}
                elif distance_atr > 1.0:
                    return {"status": "LATE", "label": "LATE", "missed": False, "late": True, "reason": f"Price {current_price} below SELL zone by {distance_atr:.1f} ATR - LATE"}
                else:
                    return {"status": "LATE", "label": "LATE - JUST BELOW ZONE", "missed": False, "late": True, "reason": f"Price just below SELL zone"}
            else:
                pct = (low - current_price) / low * 100 if low != 0 else 0
                if pct > 0.8:
                    return {"status": "MISSED", "label": "ENTRY MISSED", "missed": True, "late": False, "reason": f"Price moved {pct:.2f}% beyond SELL entry - MISSED"}
                else:
                    return {"status": "LATE", "label": "LATE", "missed": False, "late": True, "reason": f"Price below SELL zone - late"}
        if current_price > high:
            return {"status": "EARLY", "label": "WAITING FOR BOUNCE", "missed": False, "late": False, "reason": f"Price {current_price} above SELL zone {low}-{high}, waiting for bounce - EARLY stage"}
    return {"status": "UNKNOWN", "label": "UNKNOWN", "missed": False, "late": False, "reason": "Unable to determine entry status"}

def calculate_risk_reward_real(market: Dict[str, Any]) -> Dict[str, Any]:
    direction = (market.get("direction") or market.get("signal") or "WAIT").upper()
    entry_low = _safe_float(market.get("entry_low"))
    entry_high = _safe_float(market.get("entry_high"))
    sl = _safe_float(market.get("stop_loss"))
    tp1 = _safe_float(market.get("tp1"))
    tp2 = _safe_float(market.get("tp2"))
    tp3 = _safe_float(market.get("tp3"))
    if direction not in ("BUY", "SELL") or None in (entry_low, entry_high, sl):
        return {"valid": False, "risk": None, "reward1": None, "reward2": None, "reward3": None, "rr1": None, "rr2": None, "rr3": None, "reason": "Missing entry/SL for RR calculation"}
    entry = (entry_low + entry_high) / 2
    def _fmt_rr(v):
        return f"{v:.2f}" if v is not None else "N/A"
    if direction == "BUY":
        risk = entry - sl
        if risk <= 0:
            return {"valid": False, "risk": risk, "reward1": None, "rr1": None, "reason": f"Invalid BUY risk: entry {entry} <= SL {sl} - SL must be below entry"}
        r1 = (tp1 - entry) if tp1 else None
        r2 = (tp2 - entry) if tp2 else None
        r3 = (tp3 - entry) if tp3 else None
        rr1 = (r1 / risk) if r1 and risk else None
        rr2 = (r2 / risk) if r2 and risk else None
        rr3 = (r3 / risk) if r3 and risk else None
        invalid = []
        if tp1 and tp1 <= entry:
            invalid.append(f"TP1 {tp1} not above entry {entry}")
        if tp2 and tp2 <= entry:
            invalid.append(f"TP2 {tp2} not above entry")
        if tp3 and tp3 <= entry:
            invalid.append(f"TP3 {tp3} not above entry")
        valid = len(invalid) == 0 and risk > 0
        reason_str = "; ".join(invalid) if invalid else (f"BUY RR valid: risk {risk:.4f}, RR1 {_fmt_rr(rr1)} RR2 {_fmt_rr(rr2)} RR3 {_fmt_rr(rr3)}" if rr1 is not None else "RR invalid")
        return {"valid": valid, "risk": risk, "reward1": r1, "reward2": r2, "reward3": r3, "rr1": rr1, "rr2": rr2, "rr3": rr3, "reason": reason_str, "entry": entry}
    else:
        risk = sl - entry
        if risk <= 0:
            return {"valid": False, "risk": risk, "reason": f"Invalid SELL risk: SL {sl} <= entry {entry} - SL must be above entry"}
        r1 = (entry - tp1) if tp1 else None
        r2 = (entry - tp2) if tp2 else None
        r3 = (entry - tp3) if tp3 else None
        rr1 = (r1 / risk) if r1 and risk else None
        rr2 = (r2 / risk) if r2 and risk else None
        rr3 = (r3 / risk) if r3 and risk else None
        invalid = []
        if tp1 and tp1 >= entry:
            invalid.append(f"TP1 {tp1} not below entry {entry}")
        if tp2 and tp2 >= entry:
            invalid.append(f"TP2 not below entry")
        if tp3 and tp3 >= entry:
            invalid.append(f"TP3 not below entry")
        valid = len(invalid) == 0 and risk > 0
        reason_str = "; ".join(invalid) if invalid else (f"SELL RR valid: risk {risk:.4f}, RR1 {_fmt_rr(rr1)} RR2 {_fmt_rr(rr2)} RR3 {_fmt_rr(rr3)}" if rr1 is not None else "RR invalid")
        return {"valid": valid, "risk": risk, "reward1": r1, "reward2": r2, "reward3": r3, "rr1": rr1, "rr2": rr2, "rr3": rr3, "reason": reason_str, "entry": entry}

def calculate_realistic_confidence(market: Dict[str, Any], validations: Dict[str, Any]) -> Dict[str, Any]:
    base_strength = _safe_float(market.get("setup_strength") or market.get("strength") or market.get("mtf_score") or 50, 50)
    confidence = base_strength
    penalties = []
    bonuses = []
    reasons = []
    h4 = (market.get("h4_trend") or "").upper()
    h1 = (market.get("h1_trend") or "").upper()
    m15 = (market.get("m15_trend") or "").upper()
    m5 = (market.get("m5_trend") or "").upper()
    direction = (market.get("direction") or market.get("signal") or "WAIT").upper()
    if direction == "BUY":
        if h4 == "BEARISH":
            confidence -= 25
            penalties.append(("HTF 4H BEARISH vs BUY", 25))
            reasons.append("4H bearish regime vs BUY - countertrend, confidence reduced")
        if h1 == "BEARISH":
            confidence -= 15
            penalties.append(("HTF 1H BEARISH vs BUY", 15))
            reasons.append("1H bearish vs BUY - partial HTF disagreement")
        if m15 == "BEARISH":
            confidence -= 10
            penalties.append(("M15 BEARISH vs BUY", 10))
    elif direction == "SELL":
        if h4 == "BULLISH":
            confidence -= 25
            penalties.append(("HTF 4H BULLISH vs SELL", 25))
            reasons.append("4H bullish regime vs SELL - countertrend, confidence reduced")
        if h1 == "BULLISH":
            confidence -= 15
            penalties.append(("HTF 1H BULLISH vs SELL", 15))
            reasons.append("1H bullish vs SELL - partial HTF disagreement")
        if m15 == "BULLISH":
            confidence -= 10
            penalties.append(("M15 BULLISH vs SELL", 10))
    ct = validations.get("countertrend", {})
    if ct.get("is_countertrend"):
        extra = ct.get("penalty", 0) - 25
        if extra > 0:
            confidence -= extra
            penalties.append((ct.get("type"), extra))
        reasons.append(f"{ct.get('type')}: {ct.get('reason')}")
    ema_val = validations.get("ema", {})
    if ema_val.get("flat"):
        confidence -= 20
        penalties.append(("EMA FLAT", 20))
        reasons.append(ema_val.get("reason") + " - EMA signal not counted as strong confirmation")
    elif ema_val.get("alignment") in ("MIXED", "BULLISH_WEAK", "BEARISH_WEAK"):
        confidence -= 10
        penalties.append((f"EMA {ema_val.get('alignment')}", 10))
        reasons.append(ema_val.get("reason"))
    sr = validations.get("sr", {})
    if sr.get("penalty", 0) > 0:
        confidence -= sr.get("penalty")
        penalties.append((f"SR proximity {sr.get('penalty')}", sr.get("penalty")))
        reasons.append(sr.get("reason"))
    entry = validations.get("entry", {})
    if entry.get("status") == "MISSED":
        confidence = 0
        penalties.append(("ENTRY MISSED", 100))
        reasons.append(entry.get("reason") + " - must return WAIT, do not chase price")
    elif entry.get("status") == "LATE":
        confidence -= 15
        penalties.append(("LATE ENTRY", 15))
        reasons.append(entry.get("reason"))
    elif "UPPER EDGE" in entry.get("label", "") or "LOWER EDGE" in entry.get("label", ""):
        confidence -= 5
        penalties.append(("ENTRY AT EDGE", 5))
        reasons.append(entry.get("reason") + " - not EARLY")
    rr = validations.get("rr", {})
    if not rr.get("valid"):
        confidence -= 30
        penalties.append(("INVALID RR", 30))
        reasons.append(f"Risk/Reward invalid: {rr.get('reason')} - mathematically invalid setup")
    else:
        rr1 = rr.get("rr1")
        if rr1 is not None:
            if rr1 < 0.8:
                confidence -= 20
                penalties.append((f"Poor RR {rr1:.2f}", 20))
                reasons.append(f"Poor risk/reward RR1 {rr1:.2f} < 0.8 - insufficient edge")
            elif rr1 < 1.2:
                confidence -= 10
                penalties.append((f"Weak RR {rr1:.2f}", 10))
                reasons.append(f"Weak RR1 {rr1:.2f} - limited reward vs risk")
    vol_level = (market.get("volatility") or market.get("volatility_data", {}).get("level") if isinstance(market.get("volatility_data"), dict) else None)
    if isinstance(market.get("volatility_data"), dict):
        vol_level = market.get("volatility_data").get("level", vol_level)
    if vol_level == "EXTREME":
        confidence -= 15
        penalties.append(("VOLATILITY EXTREME", 15))
        reasons.append(f"Extreme volatility {market.get('atr')} - move may be over, reduces confidence")
    elif vol_level == "HIGH":
        confidence -= 5
        penalties.append(("VOLATILITY HIGH", 5))
    rsi = _safe_float(market.get("rsi"))
    if rsi is not None:
        if direction == "BUY" and rsi >= 75:
            confidence -= 12
            penalties.append((f"RSI overbought {rsi:.1f}", 12))
            reasons.append(f"RSI overbought {rsi:.1f} for BUY - exhaustion risk")
        elif direction == "BUY" and rsi >= 70:
            confidence -= 6
            penalties.append((f"RSI high {rsi:.1f}", 6))
        elif direction == "SELL" and rsi <= 25:
            confidence -= 12
            penalties.append((f"RSI oversold {rsi:.1f}", 12))
            reasons.append(f"RSI oversold {rsi:.1f} for SELL - exhaustion risk")
        elif direction == "SELL" and rsi <= 30:
            confidence -= 6
            penalties.append((f"RSI low {rsi:.1f}", 6))
    exh = market.get("exhaustion") or (market.get("exhaustion_data", {}).get("level") if isinstance(market.get("exhaustion_data"), dict) else None)
    if isinstance(market.get("exhaustion_data"), dict):
        exh = market.get("exhaustion_data").get("level", exh)
    if exh == "EXTREME":
        confidence -= 20
        penalties.append(("EXHAUSTION EXTREME", 20))
        reasons.append(f"Exhaustion EXTREME - {market.get('exhaustion_reason','move extended')}")
    elif exh == "HIGH":
        confidence -= 10
        penalties.append(("EXHAUSTION HIGH", 10))
    if market.get("late_entry"):
        confidence -= 12
        penalties.append(("LATE ENTRY FLAG", 12))
        reasons.append(f"Late entry flagged: {market.get('late_entry_reason','price extended')}")
    news_risk = (market.get("news_risk") or "LOW").upper()
    if news_risk == "HIGH":
        confidence -= 15
        penalties.append(("NEWS HIGH", 15))
        reasons.append("News risk HIGH - reduce size, increase caution")
    elif news_risk == "EXTREME":
        confidence -= 30
        penalties.append(("NEWS EXTREME", 30))
        reasons.append("News risk EXTREME - high volatility expected, avoid new entries")
    align = (market.get("timeframe_alignment") or "").upper()
    if align == "MIXED":
        confidence -= 12
        penalties.append(("MTF MIXED", 12))
        reasons.append(f"Mixed MTF alignment (4H:{h4} 1H:{h1} 15M:{m15}) - wait for alignment")
    elif "STRONG" in align and direction in ("BUY","SELL"):
        if (direction == "BUY" and "BULLISH" in align) or (direction == "SELL" and "BEARISH" in align):
            confidence += 5
            bonuses.append(("STRONG MTF ALIGNMENT", 5))
            reasons.append(f"Strong MTF alignment {align} supports {direction}")
    struct = (market.get("structure") or "").upper()
    if direction == "BUY" and struct == "BEARISH":
        confidence -= 12
        penalties.append(("STRUCTURE BEARISH vs BUY", 12))
        reasons.append(f"Market structure bearish vs BUY - structure does not support BUY")
    elif direction == "SELL" and struct == "BULLISH":
        confidence -= 12
        penalties.append(("STRUCTURE BULLISH vs SELL", 12))
        reasons.append(f"Market structure bullish vs SELL")
    confidence = max(0, min(100, int(confidence)))
    if ct.get("is_countertrend"):
        strong_evidence = False
        breakout = market.get("breakout") or (market.get("structure_data", {}).get("breakout") if isinstance(market.get("structure_data"), dict) else False)
        breakdown = market.get("breakdown") or (market.get("structure_data", {}).get("breakdown") if isinstance(market.get("structure_data"), dict) else False)
        ema_bull = ema_val.get("bullish")
        ema_bear = ema_val.get("bearish")
        mtf_score = _safe_float(market.get("mtf_score"), 50)
        if direction == "BUY" and breakout and ema_bull and mtf_score >= 70:
            strong_evidence = True
        if direction == "SELL" and breakdown and ema_bear and mtf_score <= 30:
            strong_evidence = True
        if not strong_evidence:
            if confidence >= 90:
                confidence = 74
                reasons.append(f"Countertrend {direction} capped at 74/100 HIGH not allowed without strong evidence of HTF regime break")
            elif confidence >= 80:
                confidence = min(confidence, 74)
        else:
            if confidence >= 90:
                confidence = 84
                reasons.append(f"Countertrend {direction} with strong evidence but still capped at 84 - HTF disagreement reduces confidence")
    if confidence >= 90:
        level = "EXCEPTIONAL"
    elif confidence >= 80:
        level = "STRONG"
    elif confidence >= 70:
        level = "GOOD"
    elif confidence >= 60:
        level = "MODERATE"
    elif confidence >= 50:
        level = "WEAK"
    else:
        level = "INSUFFICIENT"
    return {"confidence": confidence, "level": level, "penalties": penalties, "bonuses": bonuses, "reasons": reasons, "base_strength": base_strength}

def validate_market_signal(market: Dict[str, Any]) -> Dict[str, Any]:
    original = dict(market) if market else {}
    ok, missing = validate_data_integrity(market)
    if not ok:
        result = dict(original)
        result["signal"] = "WAIT"
        result["direction"] = "WAIT"
        result["plan_status"] = "WAIT"
        result["daily_plan_status"] = "WAIT"
        result["confidence"] = 0
        result["strength"] = 0
        result["setup_strength"] = 0
        result["reason"] = f"DATA UNAVAILABLE: {missing}"
        result["trigger_condition"] = f"DATA UNAVAILABLE: {missing}"
        result["entry_status"] = "DATA_UNAVAILABLE"
        result["entry_status_label"] = "DATA UNAVAILABLE"
        result["is_entry_missed"] = False
        result["countertrend_status"] = "NONE"
        result["validation_passed"] = False
        result["validation_errors"] = [missing]
        return result
    ema_val = validate_ema_alignment_raw(market)
    ct = detect_countertrend(market)
    sr = calculate_sr_proximity(market)
    entry = calculate_entry_status_strict(market)
    rr = calculate_risk_reward_real(market)
    validations = {"ema": ema_val, "countertrend": ct, "sr": sr, "entry": entry, "rr": rr, "data_ok": True}
    conf_result = calculate_realistic_confidence(market, validations)
    plan_status = (market.get("plan_status") or market.get("daily_plan_status") or market.get("status") or "ACTIVE").upper()
    direction = (market.get("direction") or market.get("signal") or "WAIT").upper()
    final_signal = direction
    final_reason = market.get("reason") or market.get("trigger_condition") or ""
    downgrade_reasons = []
    if entry.get("status") == "MISSED":
        final_signal = "WAIT"
        downgrade_reasons.append(entry.get("reason"))
    if not rr.get("valid"):
        final_signal = "WAIT"
        downgrade_reasons.append(rr.get("reason"))
    if conf_result["confidence"] < 50:
        final_signal = "WAIT"
        downgrade_reasons.append(f"Confidence too low {conf_result['confidence']}/100 - insufficient edge ({conf_result['level']})")
    news_risk = (market.get("news_risk") or "LOW").upper()
    if news_risk == "EXTREME" and direction in ("BUY", "SELL"):
        mtf_score = _safe_float(market.get("mtf_score"), 50)
        if not (mtf_score >= 95 or mtf_score <= 5):
            final_signal = "WAIT"
            downgrade_reasons.append(f"News risk EXTREME - avoid new entries, wait for volatility to settle (MTF {mtf_score})")
    if ema_val.get("flat") and direction in ("BUY", "SELL"):
        if conf_result["confidence"] < 65:
            final_signal = "WAIT"
            downgrade_reasons.append(ema_val.get("reason") + " - no clear EMA alignment, insufficient edge")
    if "RESISTANCE_BREAK_REQUIRED" in sr.get("flags", []) and direction == "BUY":
        if conf_result["confidence"] < 70:
            final_signal = "WAIT"
            downgrade_reasons.append(sr.get("reason"))
    if "SUPPORT_BREAK_REQUIRED" in sr.get("flags", []) and direction == "SELL":
        if conf_result["confidence"] < 70:
            final_signal = "WAIT"
            downgrade_reasons.append(sr.get("reason"))
    if plan_status == "INVALIDATED":
        final_signal = "WAIT"
        downgrade_reasons.append(f"Daily plan INVALIDATED: {market.get('invalidation_reason') or market.get('reason') or 'thesis broken'} - WAIT for new confirmed setup, do not flip opposite")
    result = dict(original)
    for key in ["daily_plan_id", "trading_date", "entry_low", "entry_high", "entry_zone", "stop_loss", "tp1", "tp2", "tp3", "take_profit", "original_price", "created_at"]:
        if key in original:
            result[key] = original[key]
    result["signal"] = final_signal
    result["direction"] = final_signal
    result["confidence"] = conf_result["confidence"]
    result["strength"] = conf_result["confidence"]
    result["setup_strength"] = conf_result["confidence"]
    result["confidence_level"] = conf_result["level"]
    result["entry_status"] = entry.get("status")
    result["entry_status_label"] = entry.get("label")
    result["entry_status_reason"] = entry.get("reason")
    result["is_entry_missed"] = entry.get("missed", False)
    result["is_entry_late"] = entry.get("late", False)
    result["countertrend_status"] = ct.get("type") if ct.get("is_countertrend") else "WITH_TREND"
    result["is_countertrend"] = ct.get("is_countertrend", False)
    result["countertrend_penalty"] = ct.get("penalty", 0)
    result["countertrend_reason"] = ct.get("reason")
    result["ema_alignment_validated"] = ema_val.get("alignment")
    result["ema_validation_reason"] = ema_val.get("reason")
    result["ema_separation_pct"] = ema_val.get("separation_pct")
    result["sr_proximity_penalty"] = sr.get("penalty", 0)
    result["sr_flags"] = sr.get("flags", [])
    result["sr_reason"] = sr.get("reason")
    result["distance_to_support_pct"] = sr.get("distance_to_support_pct")
    result["distance_to_resistance_pct"] = sr.get("distance_to_resistance_pct")
    result["risk_reward_valid"] = rr.get("valid")
    result["risk_reward_reason"] = rr.get("reason")
    result["risk_real"] = rr.get("risk")
    result["rr_real"] = rr.get("rr1")
    result["rr_tp1_real"] = rr.get("rr1")
    result["rr_tp2_real"] = rr.get("rr2")
    result["rr_tp3_real"] = rr.get("rr3")
    result["validation"] = validations
    result["confidence_breakdown"] = conf_result
    final_reasons = []
    final_reasons.append(ema_val.get("reason"))
    if ct.get("is_countertrend"):
        final_reasons.append(f"{ct.get('type')}: {ct.get('reason')} - confidence penalty {ct.get('penalty')}")
    if sr.get("reason") and sr.get("penalty", 0) > 0:
        final_reasons.append(sr.get("reason"))
    final_reasons.append(entry.get("reason"))
    if not rr.get("valid"):
        final_reasons.append(rr.get("reason"))
    else:
        if rr.get("rr1") is not None:
            final_reasons.append(f"Real RR: 1:{rr.get('rr1'):.2f} (risk {rr.get('risk'):.4f}) - {rr.get('reason')}")
    for r in conf_result["reasons"]:
        if r not in final_reasons:
            final_reasons.append(r)
    if final_signal == "WAIT":
        for dr in downgrade_reasons:
            if dr not in final_reasons:
                final_reasons.append(dr)
    if original.get("reason") and original.get("reason") not in final_reasons:
        final_reasons.insert(0, f"Original plan: {original.get('reason')}")
    result["reasons"] = final_reasons[:8]
    result["reason"] = " | ".join(final_reasons[:3]) if final_reasons else original.get("reason", "No valid setup")
    if final_signal == "WAIT":
        if entry.get("status") == "MISSED":
            result["reason"] = f"ENTRY MISSED: Original entry {original.get('entry_low')}-{original.get('entry_high')} missed, current {original.get('price')}. {entry.get('reason')}. Action: WAIT, do not chase. Original zone preserved."
            result["trigger_condition"] = result["reason"]
        elif plan_status == "INVALIDATED":
            result["reason"] = f"PLAN INVALIDATED: {original.get('invalidation_reason') or 'thesis broken'}. Action: WAIT for new confirmed setup."
            result["trigger_condition"] = result["reason"]
        else:
            result["trigger_condition"] = result["reason"]
    else:
        result["trigger_condition"] = result["reason"]
    if plan_status == "ACTIVE" and final_signal == "WAIT" and entry.get("status") != "MISSED":
        result["plan_status"] = original.get("plan_status", "ACTIVE")
        result["daily_plan_status"] = original.get("daily_plan_status", "ACTIVE")
        result["validation_downgrade"] = True
        result["validation_downgrade_reasons"] = downgrade_reasons
    else:
        result["plan_status"] = original.get("plan_status", plan_status)
        result["daily_plan_status"] = original.get("daily_plan_status", plan_status)
    result["price"] = original.get("price")
    result["current_price"] = original.get("price") or original.get("current_price")
    result["ideal_entry"] = original.get("ideal_entry") or ((original.get("entry_low") + original.get("entry_high"))/2 if original.get("entry_low") and original.get("entry_high") else original.get("price"))
    result["validation_passed"] = final_signal != "WAIT" or entry.get("status") == "MISSED" or plan_status == "INVALIDATED"
    return result

def score_signal(market: Dict[str, Any]) -> Dict[str, Any]:
    return calculate_realistic_confidence(market, {
        "ema": validate_ema_alignment_raw(market),
        "countertrend": detect_countertrend(market),
        "sr": calculate_sr_proximity(market),
        "entry": calculate_entry_status_strict(market),
        "rr": calculate_risk_reward_real(market)
    })

def is_countertrend_trade(market: Dict[str, Any]) -> bool:
    return detect_countertrend(market).get("is_countertrend", False)

def get_entry_status(market: Dict[str, Any]) -> str:
    return calculate_entry_status_strict(market).get("status", "UNKNOWN")


# =========================================================
# AI ENGINE CLASS - WITH GDELT + CRYPTO VISION + MEDIA FAILOVER
# =========================================================

class AIEngine:
    def __init__(self, memory=None):
        self.memory = memory
        self.eleven_client = None
        if ELEVENLABS_API_KEY:
            try:
                from elevenlabs import ElevenLabs
                self.eleven_client = ElevenLabs(api_key=ELEVENLABS_API_KEY)
                logger.info("✅ ElevenLabs client initialized")
            except Exception as e:
                logger.warning(f"ElevenLabs init failed: {_redact_secrets(str(e))}")
        self._tavily_module = None
        try:
            import tavily_search as _tavily
            self._tavily_module = _tavily
            if _tavily.is_tavily_configured():
                logger.info(f"✅ Tavily configured: {_tavily.provider_status()}")
            else:
                logger.info("ℹ Tavily not configured - TAVILY_API_KEY missing, continuing without web search")
        except Exception as e:
            self._tavily_module = None
            logger.info(f"ℹ Tavily module not available: {_redact_secrets(str(e))} - continuing without web search")

        if AGNES_API_KEY:
            logger.info(f"✅ Agnes AI configured | image={AGNES_IMAGE_MODEL} video={AGNES_VIDEO_MODEL}")
        else:
            logger.info("ℹ Agnes AI not configured - AGNES_API_KEY missing, image/video generation will rely on Ace Data Cloud fallback (if configured)")

        if ACEDATA_API_KEY:
            logger.info(f"✅ Ace Data Cloud fallback configured | image={ACEDATA_IMAGE_MODEL} video={ACEDATA_VIDEO_MODEL}")
        else:
            logger.info("ℹ Ace Data Cloud not configured - ACEDATA_API_KEY missing, no failover if Agnes fails")

        logger.info(f"✅ GDELT 2.0 DOC API ready (free, no key) | endpoint={GDELT_DOC_API_URL}")
        logger.info(f"✅ Crypto Vision ready (free tier) | endpoint={CRYPTOVISION_BASE_URL}")

    def _get_provider_order(self) -> List[str]:
        return ["openrouter", "groq", "gemini"]

    def _should_use_tavily(self, prompt: str) -> bool:
        if not self._tavily_module:
            return False
        try:
            if not self._tavily_module.is_tavily_configured():
                return False
            return self._tavily_module.should_trigger_tavily(prompt)
        except Exception:
            return False

    def _get_tavily_context(self, prompt: str, max_results: int = 5, search_depth: str = "basic") -> Tuple[str, List[Dict[str, str]]]:
        if not self._tavily_module or not self._should_use_tavily(prompt):
            return "", []
        try:
            query = prompt.strip()[:400]
            result = self._tavily_module.search_web(query=query, max_results=max_results, search_depth=search_depth, include_answer=True)
            if not result.get("success") or not result.get("results"):
                return "", []
            formatted = self._tavily_module.format_for_ai(result, max_content_chars=3500)
            sources = result.get("sources", [])
            return formatted, sources
        except Exception as e:
            logger.warning(f"Tavily context fetch failed: {_redact_secrets(str(e))}")
            return "", []

    def tavily_search(self, query: str, max_results: int = 5, search_depth: str = "basic") -> Dict[str, Any]:
        if not self._tavily_module:
            return {"success": False, "error": "Tavily not configured", "results": [], "sources": []}
        try:
            return self._tavily_module.search_web(query=query, max_results=max_results, search_depth=search_depth)
        except Exception as e:
            logger.warning(f"Tavily direct search failed: {_redact_secrets(str(e))}")
            return {"success": False, "error": "search_failed", "results": [], "sources": []}

    def gdelt_search(self, query: str, mode: str = "artlist", max_records: int = 10, timespan: str = "24h") -> Dict[str, Any]:
        """Public GDELT search - safe to call from bot.py / api.py."""
        return search_gdelt_doc(query=query, mode=mode, max_records=max_records, timespan=timespan)

    def crypto_vision_intelligence(self) -> Dict[str, Any]:
        """Public Crypto Vision fetch - safe to call from bot.py / api.py."""
        return get_crypto_vision_intelligence()

    def _load_memory_history(self, user_id: str, limit: int = 20) -> List[dict]:
        if not self.memory:
            return []
        try:
            history = self.memory.get_history(user_id, limit=limit)
            return history
        except Exception as e:
            logger.warning(f"Memory load failed for {user_id}: {_redact_secrets(str(e))}")
            return []

    def _load_persistent_context(self, user_id: str) -> str:
        if not self.memory:
            return ""
        parts = []
        try:
            trading_ctx = self.memory.get_trading_context(user_id)
            if trading_ctx:
                parts.append(f"TRADING PREFERENCES (from trading_preferences table):\n{trading_ctx}")
        except Exception as e:
            logger.warning(f"Trading pref load failed: {_redact_secrets(str(e))}")
        try:
            facts = self.memory.get_facts(user_id, limit=20)
            if facts:
                fact_lines = "\n".join(f"- {f['fact']} ({f.get('category','general')})" for f in facts[:10])
                parts.append(f"USER FACTS (from user_facts table - persistent):\n{fact_lines}")
        except Exception as e:
            logger.warning(f"Facts load failed: {_redact_secrets(str(e))}")
        try:
            count = self.memory.count(user_id)
            if count > 0:
                parts.append(f"PERSISTENT MEMORY STATS: {count} messages stored in ai_memory table for user {user_id}, survives restarts (king_zarry_memory.db)")
        except Exception:
            pass
        return "\n\n".join(parts)

    def _save_memory(self, user_id: str, prompt: str, response: str):
        if not self.memory:
            return
        try:
            self.memory.add_message(user_id, "user", prompt)
            self.memory.add_message(user_id, "assistant", response)
        except Exception as e:
            logger.warning(f"Memory save failed for {user_id}: {_redact_secrets(str(e))}")

    def _format_tavily_sources_footer(self, sources: List[Dict[str, str]]) -> str:
        if not sources:
            return ""
        lines = []
        for s in sources[:5]:
            title = (s.get("title") or "source").strip()
            url = (s.get("url") or "").strip()
            if url:
                lines.append(f"- [{title}]({url})")
            else:
                lines.append(f"- {title}")
        if not lines:
            return ""
        return "\n\n📰 **Sources:**\n" + "\n".join(lines)

    # =====================================================
    # 🎨 AGNES + ACEDATA MEDIA ROUTING
    # =====================================================
    def _route_media_request(self, user_id: str, prompt: str, intent: Dict[str, Any], image: Optional[Tuple[str, bytes]]) -> Optional[str]:
        kind = intent.get("kind")
        agnes_ok = bool(AGNES_API_KEY)
        acedata_ok = bool(ACEDATA_API_KEY)

        if not agnes_ok and not acedata_ok:
            logger.warning("Media intent detected but neither AGNES_API_KEY nor ACEDATA_API_KEY is set")
            return (
                "🎨 I'd love to make that for you, but image/video generation isn't configured on this server yet. "
                "Ask the admin to set `AGNES_API_KEY` (primary) and/or `ACEDATA_API_KEY` (fallback) on Railway. "
                "Meanwhile, I'm still here for trading, alerts, news, and chat."
            )

        try:
            if kind == "image":
                logger.info(f"Image generation request -> user={str(user_id)[:3]}***")
                result = {"success": False}
                if agnes_ok:
                    result = agnes_generate_image(prompt=intent["prompt"], size=intent.get("size", "1024x1024"))
                    if not result.get("success"):
                        logger.warning(f"Agnes image generation failed ({result.get('error')}) - falling back to Ace Data Cloud")
                if not result.get("success") and acedata_ok:
                    result = acedata_generate_image(prompt=intent["prompt"])
                if result.get("success") and result.get("url"):
                    url = result["url"]
                    provider = result.get("provider", "agnes")
                    reply = f"🎨 Done! Here's your image:\n\n![Generated Image]({url})\n\n**Direct link:** {url}\n_Model: {result.get('model')} ({provider})_"
                    self._save_memory(user_id, prompt, f"[image generated] {url}")
                    return reply
                err = result.get("error") or "unknown_error"
                logger.warning(f"Image generation failed on all providers: {_redact_secrets(str(err))}")
                return f"🎨 I tried to generate that image but ran into an error ({err}). Try again in a moment or rephrase the prompt."

            if kind == "image_edit":
                if not image:
                    return "🎨 To edit an image, please attach the image along with your edit request."
                try:
                    mime, img_bytes = image
                    b64 = base64.b64encode(img_bytes).decode("utf-8")
                    data_uri = f"data:{mime};base64,{b64}"
                except Exception as e:
                    logger.warning(f"Failed to encode input image: {_redact_secrets(str(e))}")
                    return "🎨 I couldn't read the attached image. Please try re-uploading it."
                logger.info(f"Image edit request -> user={str(user_id)[:3]}***")
                result = {"success": False}
                if agnes_ok:
                    result = agnes_edit_image(prompt=intent["prompt"], image_url=data_uri, size=intent.get("size", "1024x1024"))
                    if not result.get("success"):
                        logger.warning(f"Agnes image edit failed ({result.get('error')}) - falling back to Ace Data Cloud")
                if not result.get("success") and acedata_ok:
                    result = acedata_edit_image(prompt=intent["prompt"], image_url=data_uri)
                if result.get("success") and result.get("url"):
                    url = result["url"]
                    provider = result.get("provider", "agnes")
                    reply = f"🎨 Edited it! Here's the result:\n\n![Edited Image]({url})\n\n**Direct link:** {url}\n_Model: {result.get('model')} (image-to-image, {provider})_"
                    self._save_memory(user_id, prompt, f"[image edited] {url}")
                    return reply
                err = result.get("error") or "unknown_error"
                logger.warning(f"Image edit failed on all providers: {_redact_secrets(str(err))}")
                return f"🎨 I tried to edit that image but ran into an error ({err}). Try again or adjust your edit."

            if kind == "video":
                logger.info(f"Video generation request -> user={str(user_id)[:3]}***")
                mode = intent.get("mode", "text")
                task = {"success": False}
                used_provider = None
                if agnes_ok:
                    task = agnes_create_video(prompt=intent["prompt"], seconds=intent.get("seconds", 5), size=intent.get("size", "720P"), aspect_ratio=intent.get("aspect_ratio", "16:9"), mode=mode)
                    if task.get("success") and task.get("video_id"):
                        used_provider = "agnes"
                    else:
                        logger.warning(f"Agnes video task creation failed ({task.get('error')}) - falling back to Ace Data Cloud")
                if not (task.get("success") and task.get("video_id")) and acedata_ok:
                    task = acedata_create_video(prompt=intent["prompt"], aspect_ratio=intent.get("aspect_ratio", "16:9"))
                    if task.get("success"):
                        used_provider = "acedata"
                if not task.get("success") or (not task.get("video_id") and not task.get("url")):
                    err = task.get("error") or "unknown_error"
                    logger.warning(f"Video task creation failed on all providers: {_redact_secrets(str(err))}")
                    return f"🎬 I couldn't start the video task ({err}). Try again in a moment."
                if used_provider == "acedata" and task.get("url"):
                    url = task["url"]
                    reply = f"🎬 Your video is ready!\n\n[▶ Watch Video]({url})\n\n**Direct link:** {url}\n_Model: {ACEDATA_VIDEO_MODEL} (acedata)_"
                    self._save_memory(user_id, prompt, f"[video generated] {url}")
                    return reply
                video_id = task["video_id"]
                logger.info(f"Video task created via {used_provider}: {video_id} - polling for completion")
                if used_provider == "agnes":
                    poll = agnes_poll_video(video_id, max_wait=AGNES_VIDEO_POLL_TIMEOUT)
                else:
                    poll = acedata_poll_video(video_id, max_wait=ACEDATA_VIDEO_POLL_TIMEOUT)
                if poll.get("success") and poll.get("url"):
                    url = poll["url"]
                    model_name = AGNES_VIDEO_MODEL if used_provider == "agnes" else ACEDATA_VIDEO_MODEL
                    reply = f"🎬 Your video is ready!\n\n[▶ Watch Video]({url})\n\n**Direct link:** {url}\n_Model: {model_name} | Task ID: {video_id} ({used_provider})_"
                    self._save_memory(user_id, prompt, f"[video generated] {url}")
                    return reply
                if poll.get("status") == "timeout":
                    reply = f"🎬 Video is still rendering ({used_provider}, this can take a couple of minutes for longer clips).\n\n**Task ID:** `{video_id}`\nAsk me again in a minute and I'll check the status, or use the video ID to track it."
                    self._save_memory(user_id, prompt, f"[video pending] task={video_id} provider={used_provider}")
                    return reply
                err = poll.get("error") or "unknown_error"
                if used_provider == "agnes" and acedata_ok:
                    logger.info("Agnes video poll failed - attempting one-shot Ace Data Cloud video fallback")
                    fallback_task = acedata_create_video(prompt=intent["prompt"], aspect_ratio=intent.get("aspect_ratio", "16:9"))
                    if fallback_task.get("success") and fallback_task.get("url"):
                        url = fallback_task["url"]
                        reply = f"🎬 Your video is ready!\n\n[▶ Watch Video]({url})\n\n**Direct link:** {url}\n_Model: {ACEDATA_VIDEO_MODEL} (acedata fallback)_"
                        self._save_memory(user_id, prompt, f"[video generated] {url}")
                        return reply
                    elif fallback_task.get("success") and fallback_task.get("video_id"):
                        fallback_poll = acedata_poll_video(fallback_task["video_id"], max_wait=ACEDATA_VIDEO_POLL_TIMEOUT)
                        if fallback_poll.get("success") and fallback_poll.get("url"):
                            url = fallback_poll["url"]
                            reply = f"🎬 Your video is ready!\n\n[▶ Watch Video]({url})\n\n**Direct link:** {url}\n_Model: {ACEDATA_VIDEO_MODEL} (acedata fallback)_"
                            self._save_memory(user_id, prompt, f"[video generated] {url}")
                            return reply
                logger.warning(f"Video task failed on all providers: {_redact_secrets(str(err))}")
                return f"🎬 The video task failed ({err}). Try again or shorten the prompt."

        except Exception as e:
            logger.error(f"Media routing crashed: {_redact_secrets(str(e))}")
            return None
        return None

    def _call_providers(self, prompt_text: str, history, image, persistent_ctx: str, casual: bool = False):
        providers = self._get_provider_order()
        seen = set()
        finite_providers = []
        for p in providers:
            if p not in seen:
                seen.add(p)
                finite_providers.append(p)
        last_err = None
        for provider in finite_providers:
            try:
                resp = None
                if provider == "openrouter" and OPENROUTER_API_KEY:
                    resp = self._openrouter(prompt_text, history, image, persistent_ctx, casual)
                elif provider == "groq" and GROQ_API_KEY:
                    resp = self._groq(prompt_text, history, image, persistent_ctx, casual)
                elif provider == "gemini" and GEMINI_API_KEY:
                    resp = self._gemini(prompt_text, history, image, persistent_ctx, casual)
                elif provider == "openai" and OPENROUTER_API_KEY:
                    resp = self._openrouter(prompt_text, history, image, persistent_ctx, casual)
                else:
                    continue
                if resp:
                    cleaned = clean_ai_response(resp)
                    if cleaned:
                        return cleaned
            except Exception as e:
                last_err = _sanitize_exception_message(e)
                continue
        logger.error(f"All providers failed: {last_err}")
        return None

    def ask(self, user_id: str, prompt: str, image=None) -> str:
        user_id = str(user_id)
        original_prompt = str(prompt or "").strip()
        prompt_for_providers = original_prompt
        if not prompt_for_providers and not image:
            return "Hey, I'm listening 👀 what's on your mind?"

        # --- Video status check ---
        try:
            vm = _VIDEO_STATUS_CHECK_PATTERN.search(original_prompt)
        except Exception:
            vm = None
        if vm:
            candidate_id = vm.group(1)
            if not re.match(r"^https?://", candidate_id, re.IGNORECASE):
                try:
                    logger.info(f"Video status check requested for task id={candidate_id[:6]}***")
                    poll = {"success": False}
                    if AGNES_API_KEY:
                        poll = agnes_poll_video(candidate_id, max_wait=30)
                    if not poll.get("success") and ACEDATA_API_KEY:
                        poll = acedata_poll_video(candidate_id, max_wait=30)
                    if poll.get("success") and poll.get("url"):
                        url = poll["url"]
                        reply = f"🎬 Video `{candidate_id}` is ready!\n\n[▶ Watch Video]({url})\n\n**Direct link:** {url}"
                        self._save_memory(user_id, original_prompt, reply)
                        return reply
                    status = poll.get("status") or "unknown"
                    err = poll.get("error") or ""
                    if status == "timeout":
                        reply = f"🎬 Task `{candidate_id}` is still rendering. Try again in a minute."
                    elif status == "failed":
                        reply = f"🎬 Task `{candidate_id}` failed. {err}".strip()
                    else:
                        reply = f"🎬 Task `{candidate_id}` status: **{status}**. {err}".strip()
                    self._save_memory(user_id, original_prompt, reply)
                    return reply
                except Exception as e:
                    logger.warning(f"Video status check crashed: {_redact_secrets(str(e))}")

        # --- Media intent check (before text providers) ---
        try:
            media_intent = _detect_media_intent(original_prompt, has_image=bool(image))
        except Exception:
            media_intent = None
        if media_intent:
            media_reply = self._route_media_request(user_id, original_prompt, media_intent, image)
            if media_reply:
                return media_reply
            logger.info("Media routing returned None - falling back to text provider")

        needs_web = False
        try:
            needs_web = bool(original_prompt) and self._should_use_tavily(original_prompt)
        except Exception:
            needs_web = False
        casual = _is_casual_chat(original_prompt, has_image=bool(image), needs_web=needs_web)

        history = self._load_memory_history(user_id, limit=20 if casual else 15)
        persistent_ctx = self._load_persistent_context(user_id)

        # --- Tavily ---
        tavily_context = ""
        tavily_sources = []
        try:
            if original_prompt and needs_web:
                lower = original_prompt.lower()
                wants_deep = any(k in lower for k in ["deep research", "detailed research", "comprehensive research", "thorough research", "in-depth"])
                depth = "advanced" if wants_deep else "basic"
                max_res = 6 if wants_deep else 5
                ctx, srcs = self._get_tavily_context(original_prompt, max_results=max_res, search_depth=depth)
                if ctx:
                    tavily_context = ctx
                    tavily_sources = srcs
                    prompt_for_providers = f"{original_prompt}\n\n--- LIVE WEB SEARCH CONTEXT (Tavily) ---\n{tavily_context}\n--- END WEB CONTEXT ---\n"
        except Exception as e:
            logger.warning(f"Tavily failed: {_redact_secrets(str(e))}")

        # --- GDELT 2.0 DOC API (free, global news intelligence) ---
        gdelt_context = ""
        try:
            if original_prompt and not casual and _should_use_gdelt(original_prompt):
                gdelt_result = search_gdelt_doc(
                    query=original_prompt,
                    mode="artlist",
                    max_records=GDELT_MAX_RECORDS,
                    timespan="24h",
                    sort="hybridrel",
                )
                if gdelt_result.get("success"):
                    gdelt_context = format_gdelt_for_ai(gdelt_result, max_articles=5)
                    if gdelt_context:
                        prompt_for_providers = f"{prompt_for_providers}\n\n{gdelt_context}\n"
        except Exception as e:
            logger.warning(f"GDELT failed: {_redact_secrets(str(e))}")

        # --- Crypto Vision (free crypto intelligence) ---
        cryptovision_context = ""
        try:
            if original_prompt and not casual and _should_use_cryptovision(original_prompt):
                cv_intel = get_crypto_vision_intelligence()
                cryptovision_context = format_crypto_vision_for_ai(cv_intel, max_items=5)
                if cryptovision_context:
                    prompt_for_providers = f"{prompt_for_providers}\n\n{cryptovision_context}\n"
        except Exception as e:
            logger.warning(f"Crypto Vision failed: {_redact_secrets(str(e))}")

        first_response = self._call_providers(prompt_for_providers, history, image, persistent_ctx, casual)
        if not first_response:
            return "My brain lagged for a sec 😅 try me again in a moment."

        if _detect_forbidden_tool_attempts(first_response):
            logger.warning(f"Forbidden tool attempt blocked for user {user_id[:3]}***")
            lower_orig = original_prompt.lower()
            is_alert_intent = any(k in lower_orig for k in ["my alert", "show my alert", "alert status", "what alert", "how many alert", "triggered alert", "active alert", "check my alert", "show me my alert", "my alerts"])
            if is_alert_intent:
                tool_result = _execute_safe_tool("get_user_alert_status", user_id)
                tool_json = json.dumps(tool_result, indent=2, default=str)
                second_prompt = f"User asked: {original_prompt}\n\nTool get_user_alert_status executed securely. Result:\n{tool_json}\n\nNow generate final human-readable answer about their alerts. Do NOT include any <tool_call> markup, SQL, or database paths."
                second_resp = self._call_providers(second_prompt, history, None, persistent_ctx)
                if second_resp:
                    final_clean = _sanitize_final_response(second_resp)
                    final_clean = clean_ai_response(final_clean)
                    if final_clean:
                        self._save_memory(user_id, original_prompt, final_clean)
                        logger.info("Final response generated after blocked forbidden tool")
                        return final_clean
            sanitized = _sanitize_final_response(first_response)
            if not sanitized or len(sanitized) < 10:
                return "Sorry, I couldn't pull that up because of a security rule 🔒 Try rephrasing, e.g. 'Show my alerts'."
            self._save_memory(user_id, original_prompt, sanitized)
            return sanitized

        tool_requests = _detect_tool_requests(first_response)
        if tool_requests:
            tool_name = tool_requests[0]
            logger.info(f"Allowed tool detected: {tool_name}")
            if "user 12345" in original_prompt.lower():
                logger.warning("Potential cross-user request - enforcing authenticated id")
            tool_result = _execute_safe_tool(tool_name, user_id)
            tool_json = json.dumps(tool_result, indent=2, default=str)
            second_prompt = f"User asked: {original_prompt}\n\nTool {tool_name} executed securely. Result:\n{tool_json}\n\nGenerate final answer: human-readable alert status. Include total, active, triggered and list.Do NOT include <tool_call>, SQL, or db paths."
            second_resp = self._call_providers(second_prompt, history, None, persistent_ctx)
            if second_resp:
                final_clean = _sanitize_final_response(second_resp)
                final_clean = clean_ai_response(final_clean)
                if final_clean:
                    self._save_memory(user_id, original_prompt, final_clean)
                    logger.info("Final response generated after tool execution")
                    return final_clean
            if not tool_result.get("success"):
                return "I couldn't pull up your alerts right now 😕 Give me a moment and try again."
            total = tool_result.get("total_alerts", 0)
            active = tool_result.get("active_alerts", 0)
            triggered = tool_result.get("triggered_alerts", 0)
            alerts = tool_result.get("alerts", [])
            if total == 0:
                fallback = "🔔 You currently have no alerts. Use /alert XAU above 4329 to create one."
            else:
                lines = [f"🔔 You have {total} alerts ({active} active, {triggered} triggered):"]
                for a in alerts[:10]:
                    status = "✅ Active" if a["active"] else "⏸ Inactive"
                    if a["triggered"]:
                        status += " 🎯 Triggered"
                    lines.append(f"• {a['symbol']} {a['condition']} {a['target_price']} - {status} (ID: {a['id']})")
                fallback = "\n".join(lines)
            self._save_memory(user_id, original_prompt, fallback)
            return fallback

        final = _sanitize_final_response(first_response)
        final = clean_ai_response(final)
        if not final:
            final = "Hmm, I blanked out there 😅 say that again for me?"

        if tavily_sources:
            footer = self._format_tavily_sources_footer(tavily_sources)
            if footer and "**Sources:**" not in final and "Sources:" not in final:
                final = final + footer

        self._save_memory(user_id, original_prompt, final)
        return final

    def _build_openai_messages(self, prompt: str, history: List[dict], image: Optional[Tuple[str, bytes]], persistent_ctx: str = "", include_system: bool = True, casual: bool = False) -> List[dict]:
        messages = []
        if include_system:
            sys_content = CASUAL_SYSTEM_PROMPT if casual else SYSTEM_PROMPT
            if persistent_ctx:
                sys_content += f"\n\n--- PERSISTENT MEMORY FOR USER (from king_zarry_memory.db - survives restarts) ---\n{persistent_ctx}\n--- END PERSISTENT MEMORY ---"
            messages.append({"role": "system", "content": sys_content})
        if persistent_ctx and not include_system:
            messages.append({"role": "system", "content": f"PERSISTENT MEMORY:\n{persistent_ctx}"})
        elif persistent_ctx and include_system:
            pass
        history_window = 20 if casual else 10
        for h in history[-history_window:]:
            role = h.get("role", "user")
            content = h.get("content", "")
            if role in ["user", "assistant"] and content:
                messages.append({"role": role, "content": content})
        if image:
            mime, img_bytes = image
            b64 = base64.b64encode(img_bytes).decode("utf-8")
            messages.append({"role": "user", "content": [{"type": "text", "text": prompt}, {"type": "image_url", "image_url": {"url": f"data:{mime};base64,{b64}"}}]})
        else:
            messages.append({"role": "user", "content": prompt})
        return messages

    def _request_with_retry(self, url, headers, json_payload, provider_name: str, max_retries: int = 1, timeout: int = 45):
        last_exc = None
        for attempt in range(max_retries + 1):
            try:
                resp = requests.post(url, headers=headers, json=json_payload, timeout=timeout)
                if resp.status_code == 429:
                    body = _redact_secrets(resp.text[:500])
                    logger.warning(f"{provider_name} provider failed with HTTP 429, attempt {attempt+1}/{max_retries+1}. Body: {body[:200]}")
                    if attempt < max_retries:
                        time.sleep(0.6 * (attempt + 1))
                        continue
                    raise ProviderRateLimitError(f"{provider_name} rate limit 429")
                if resp.status_code in (500, 502, 503, 504):
                    body = _redact_secrets(resp.text[:500])
                    logger.warning(f"{provider_name} transient HTTP {resp.status_code}, attempt {attempt+1}/{max_retries+1}. Body: {body[:200]}")
                    if attempt < max_retries:
                        time.sleep(0.8 * (attempt + 1))
                        continue
                    raise ProviderTransientError(f"{provider_name} transient HTTP {resp.status_code}")
                if resp.status_code >= 400:
                    body = _redact_secrets(resp.text[:500])
                    if _is_rate_limit_error(resp.status_code, body):
                        if attempt < max_retries:
                            time.sleep(0.6 * (attempt + 1))
                            continue
                        raise ProviderRateLimitError(f"{provider_name} rate limit {resp.status_code}: {body[:200]}")
                    if _is_transient_error(resp.status_code, body):
                        if attempt < max_retries:
                            time.sleep(0.8 * (attempt + 1))
                            continue
                        raise ProviderTransientError(f"{provider_name} transient {resp.status_code}: {body[:200]}")
                    raise RuntimeError(_redact_secrets(f"HTTP {resp.status_code}: {body[:200]}"))
                return resp
            except ProviderRateLimitError:
                raise
            except ProviderTransientError:
                raise
            except requests.exceptions.Timeout as e:
                last_exc = e
                logger.warning(f"{provider_name} timeout attempt {attempt+1}/{max_retries+1}")
                if attempt < max_retries:
                    time.sleep(0.8 * (attempt + 1))
                    continue
                raise ProviderTransientError(f"{provider_name} timeout")
            except requests.exceptions.ConnectionError as e:
                last_exc = e
                msg = _redact_secrets(str(e))
                logger.warning(f"{provider_name} connection error attempt {attempt+1}/{max_retries+1}: {msg[:200]}")
                if attempt < max_retries:
                    time.sleep(0.8 * (attempt + 1))
                    continue
                raise ProviderTransientError(f"{provider_name} connection error")
            except requests.exceptions.HTTPError as e:
                sanitized = _sanitize_exception_message(e)
                status = getattr(e.response, 'status_code', None) if hasattr(e, 'response') else None
                if _is_rate_limit_error(status, sanitized):
                    if attempt < max_retries:
                        time.sleep(0.6 * (attempt + 1))
                        continue
                    raise ProviderRateLimitError(f"{provider_name} rate limit from HTTPError: {sanitized[:200]}")
                if _is_transient_error(status, sanitized):
                    if attempt < max_retries:
                        time.sleep(0.8 * (attempt + 1))
                        continue
                    raise ProviderTransientError(f"{provider_name} transient from HTTPError: {sanitized[:200]}")
                raise RuntimeError(sanitized)
            except Exception as e:
                sanitized = _sanitize_exception_message(e)
                if _is_rate_limit_error(None, sanitized):
                    if attempt < max_retries:
                        time.sleep(0.6 * (attempt + 1))
                        continue
                    raise ProviderRateLimitError(f"{provider_name} rate limit: {sanitized[:200]}")
                if _is_transient_error(None, sanitized):
                    if attempt < max_retries:
                        time.sleep(0.8 * (attempt + 1))
                        continue
                    raise ProviderTransientError(f"{provider_name} transient: {sanitized[:200]}")
                raise RuntimeError(sanitized)
        if last_exc:
            raise ProviderTransientError(f"{provider_name} failed after retries: {_sanitize_exception_message(last_exc)}")
        raise ProviderTransientError(f"{provider_name} failed after retries")

    def _xai(self, prompt: str, history: List[dict], image: Optional[Tuple[str, bytes]], persistent_ctx: str = "", casual: bool = False) -> Optional[str]:
        if not XAI_API_KEY:
            return None
        model = XAI_MODEL
        messages = self._build_openai_messages(prompt, history, image, persistent_ctx, casual=casual)
        headers = {"Authorization": f"Bearer {XAI_API_KEY}", "Content-Type": "application/json"}
        payload = {"model": model, "messages": messages, "temperature": 0.85 if casual else 0.7, "max_tokens": 2000}
        resp = self._request_with_retry(XAI_URL, headers, payload, "xai", max_retries=1, timeout=45)
        data = resp.json()
        return data["choices"][0]["message"]["content"]

    def _groq(self, prompt: str, history: List[dict], image: Optional[Tuple[str, bytes]], persistent_ctx: str = "", casual: bool = False) -> Optional[str]:
        if not GROQ_API_KEY:
            return None
        model = GROQ_VISION_MODEL if image else GROQ_MODEL
        messages = self._build_openai_messages(prompt, history, image, persistent_ctx, casual=casual)
        headers = {"Authorization": f"Bearer {GROQ_API_KEY}", "Content-Type": "application/json"}
        payload = {"model": model, "messages": messages, "temperature": 0.85 if casual else 0.7, "max_tokens": 2000}
        resp = self._request_with_retry(GROQ_URL, headers, payload, "groq", max_retries=1, timeout=45)
        data = resp.json()
        return data["choices"][0]["message"]["content"]

    def _openrouter(self, prompt: str, history: List[dict], image: Optional[Tuple[str, bytes]], persistent_ctx: str = "", casual: bool = False) -> Optional[str]:
        if not OPENROUTER_API_KEY:
            return None
        model = OPENROUTER_MODEL
        messages = self._build_openai_messages(prompt, history, image, persistent_ctx, casual=casual)
        headers = {"Authorization": f"Bearer {OPENROUTER_API_KEY}", "Content-Type": "application/json"}
        payload = {"model": model, "messages": messages, "temperature": 0.85 if casual else 0.7, "max_tokens": 2000}
        resp = self._request_with_retry(OPENROUTER_URL, headers, payload, "openrouter", max_retries=1, timeout=45)
        data = resp.json()
        return data["choices"][0]["message"]["content"]

    def _openai(self, prompt: str, history: List[dict], image: Optional[Tuple[str, bytes]], persistent_ctx: str = "", casual: bool = False) -> Optional[str]:
        return self._openrouter(prompt, history, image, persistent_ctx, casual)

    def _gemini(self, prompt: str, history: List[dict], image: Optional[Tuple[str, bytes]], persistent_ctx: str = "", casual: bool = False) -> Optional[str]:
        if not GEMINI_API_KEY:
            return None
        contents = []
        history_window = 16 if casual else 8
        for h in history[-history_window:]:
            role = h.get("role")
            content = h.get("content")
            if not content:
                continue
            g_role = "user" if role == "user" else "model"
            contents.append({"role": g_role, "parts": [{"text": content}]})
        if image:
            mime, img_bytes = image
            b64 = base64.b64encode(img_bytes).decode("utf-8")
            parts = [{"text": prompt}, {"inline_data": {"mime_type": mime, "data": b64}}]
            contents.append({"role": "user", "parts": parts})
        else:
            contents.append({"role": "user", "parts": [{"text": prompt}]})
        sys_text = CASUAL_SYSTEM_PROMPT if casual else SYSTEM_PROMPT
        if persistent_ctx:
            sys_text += f"\n\n--- PERSISTENT MEMORY FOR USER (king_zarry_memory.db) ---\n{persistent_ctx}\n--- END ---"
        payload = {"contents": contents, "systemInstruction": {"parts": [{"text": sys_text}]}, "generationConfig": {"temperature": 0.85 if casual else 0.7, "maxOutputTokens": 2000}}
        url = GEMINI_URL.format(model=GEMINI_MODEL) + f"?key={GEMINI_API_KEY}"
        headers = {"Content-Type": "application/json"}
        resp = self._request_with_retry(url, headers, payload, "gemini", max_retries=1, timeout=45)
        data = resp.json()
        try:
            candidates = data.get("candidates", [])
            if not candidates:
                return None
            parts = candidates[0].get("content", {}).get("parts", [])
            text = "".join(p.get("text","") for p in parts)
            return text
        except Exception as e:
            logger.warning(f"Gemini parse error: {_redact_secrets(str(e))}")
            return None

    def generate_speech(self, text: str) -> io.BytesIO:
        if not text:
            raise ValueError("Text empty")
        text = str(text).strip()[:800]
        if self.eleven_client and ELEVENLABS_API_KEY:
            try:
                logger.info(f"TTS provider: ElevenLabs | TTS model: {ELEVENLABS_MODEL_ID} | TTS voice: Bella ({ELEVENLABS_VOICE_ID})")
                audio = self.eleven_client.text_to_speech.convert(voice_id=ELEVENLABS_VOICE_ID, model_id=ELEVENLABS_MODEL_ID, text=text)
                bio = io.BytesIO()
                for chunk in audio:
                    if chunk:
                        bio.write(chunk)
                bio.seek(0)
                bio.name = "voice.mp3"
                return bio
            except Exception as e:
                logger.warning(f"ElevenLabs TTS failed: {_redact_secrets(str(e))}")
                raise
        else:
            raise RuntimeError("ElevenLabs not configured")

    def validate_market(self, market_data: Dict[str, Any]) -> Dict[str, Any]:
        return validate_market_signal(market_data)

    def validate_and_score(self, market_data: Dict[str, Any]) -> Dict[str, Any]:
        return validate_market_signal(market_data)

    def provider_status(self) -> Dict[str, Any]:
        """Return a summary of configured providers. No secrets exposed."""
        return {
            "chain": self._get_provider_order(),
            "openrouter": bool(OPENROUTER_API_KEY),
            "groq": bool(GROQ_API_KEY),
            "gemini": bool(GEMINI_API_KEY),
            "elevenlabs": bool(self.eleven_client),
            "agnes": bool(AGNES_API_KEY),
            "agnes_image": AGNES_IMAGE_MODEL,
            "agnes_video": AGNES_VIDEO_MODEL,
            "acedata": bool(ACEDATA_API_KEY),
            "acedata_image": ACEDATA_IMAGE_MODEL,
            "acedata_video": ACEDATA_VIDEO_MODEL,
            "media_failover_active": bool(AGNES_API_KEY) and bool(ACEDATA_API_KEY),
            "tavily": bool(self._tavily_module and getattr(self._tavily_module, "is_tavily_configured", lambda: False)()),
            "gdelt": True,
            "gdelt_endpoint": GDELT_DOC_API_URL,
            "cryptovision": True,
            "cryptovision_endpoint": CRYPTOVISION_BASE_URL,
        }

    def generate_image(self, prompt: str, size: str = "1024x1024") -> Dict[str, Any]:
        if AGNES_API_KEY:
            result = agnes_generate_image(prompt=prompt, size=size)
            if result.get("success"):
                return result
        if ACEDATA_API_KEY:
            return acedata_generate_image(prompt=prompt)
        return {"success": False, "url": None, "error": "no_provider_configured"}

    def edit_image(self, prompt: str, image_url: str, size: str = "1024x1024") -> Dict[str, Any]:
        if AGNES_API_KEY:
            result = agnes_edit_image(prompt=prompt, image_url=image_url, size=size)
            if result.get("success"):
                return result
        if ACEDATA_API_KEY:
            return acedata_edit_image(prompt=prompt, image_url=image_url)
        return {"success": False, "url": None, "error": "no_provider_configured"}

    def generate_video(self, prompt: str, seconds: int = 5, size: str = "720P", aspect_ratio: str = "16:9", mode: str = "text") -> Dict[str, Any]:
        if AGNES_API_KEY:
            result = agnes_create_video(prompt=prompt, seconds=seconds, size=size, aspect_ratio=aspect_ratio, mode=mode)
            if result.get("success"):
                return result
        if ACEDATA_API_KEY:
            return acedata_create_video(prompt=prompt, aspect_ratio=aspect_ratio)
        return {"success": False, "video_id": None, "error": "no_provider_configured"}

    def poll_video(self, video_id: str, max_wait: Optional[int] = None, provider: Optional[str] = None) -> Dict[str, Any]:
        if provider == "acedata":
            return acedata_poll_video(video_id=video_id, max_wait=max_wait)
        if provider == "agnes":
            return agnes_poll_video(video_id=video_id, max_wait=max_wait)
        if AGNES_API_KEY:
            result = agnes_poll_video(video_id=video_id, max_wait=max_wait)
            if result.get("success") or result.get("status") not in ("error",):
                return result
        if ACEDATA_API_KEY:
            return acedata_poll_video(video_id=video_id, max_wait=max_wait)
        return {"success": False, "status": "error", "error": "no_provider_configured"}

    def is_media_enabled(self) -> bool:
        return bool(AGNES_API_KEY) or bool(ACEDATA_API_KEY)


# =========================================================
# 🧩 MODULE-LEVEL SINGLETON
# =========================================================
_instance: Optional[AIEngine] = None

def get_ai_engine(memory=None) -> AIEngine:
    global _instance
    if _instance is None:
        _instance = AIEngine(memory=memory)
    elif memory is not None and _instance.memory is None:
        _instance.memory = memory
    return _instance


def reset_ai_engine():
    global _instance
    _instance = None
