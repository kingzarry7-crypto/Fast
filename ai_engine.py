import os
import re
import io
import json
import base64
import logging
from typing import Optional, Tuple, List
import requests

logger = logging.getLogger("ai_engine")

def clean_env_str(v, default=""):
    if not v:
        return default
    v = re.sub(r"[\u200b\u200c\u200d\u2060\ufeff]", "", str(v)).strip()
    return v if v else default

# Env
GROQ_API_KEY = clean_env_str(os.getenv("GROQ_API_KEY"))
GROQ_MODEL = clean_env_str(os.getenv("GROQ_MODEL"), "llama-3.3-70b-versatile")
GROQ_VISION_MODEL = clean_env_str(os.getenv("GROQ_VISION_MODEL"), "meta-llama/llama-4-scout-17b-16e-instruct")
GROQ_URL = clean_env_str(os.getenv("GROQ_URL"), "https://api.groq.com/openai/v1/chat/completions")

GEMINI_API_KEY = clean_env_str(os.getenv("GEMINI_API_KEY"))
GEMINI_MODEL = clean_env_str(os.getenv("GEMINI_MODEL"), "gemini-2.5-flash")
GEMINI_URL = "https://generativelanguage.googleapis.com/v1beta/models/{model}:generateContent"

OPENAI_API_KEY = clean_env_str(os.getenv("OPENAI_API_KEY"))
OPENAI_MODEL = clean_env_str(os.getenv("OPENAI_MODEL"), "gpt-4o-mini")
OPENAI_URL = clean_env_str(os.getenv("OPENAI_URL"), "https://api.openai.com/v1/chat/completions")

XAI_API_KEY = clean_env_str(os.getenv("XAI_API_KEY") or os.getenv("GROK_API_KEY"))
XAI_MODEL = clean_env_str(os.getenv("XAI_MODEL") or os.getenv("GROK_MODEL"), "grok-4")
XAI_URL = clean_env_str(os.getenv("XAI_BASE_URL") or os.getenv("GROQ_BASE_URL"), "https://api.x.ai/v1/chat/completions")
# If XAI_BASE_URL contains x.ai use it, else default x.ai
if "x.ai" not in XAI_URL and XAI_API_KEY:
    # If user set GROQ URL but has XAI key, still use x.ai for XAI provider
    if "groq" not in XAI_URL.lower():
        XAI_URL = "https://api.x.ai/v1/chat/completions"
    else:
        # env var was actually GROQ, so we need separate
        XAI_URL = clean_env_str(os.getenv("XAI_BASE_URL"), "https://api.x.ai/v1/chat/completions")

AI_PROVIDER = clean_env_str(os.getenv("AI_PROVIDER"), "AUTO").upper()

ELEVENLABS_API_KEY = clean_env_str(os.getenv("ELEVENLABS_API_KEY"))
ELEVENLABS_VOICE_ID = clean_env_str(os.getenv("ELEVENLABS_VOICE_ID"), "21m00Tcm4TlvDq8ikWAM")
ELEVENLABS_MODEL_ID = clean_env_str(os.getenv("ELEVENLABS_MODEL_ID"), "eleven_flash_v2_5")

SYSTEM_PROMPT = """
You are King Zarry AI 👑 - Advanced Trading & Intelligence Assistant.

Personality:
- Confident, sharp, professional trader and AI assistant
- Direct, no fluff, actionable
- Never reveal internal chain-of-thought
- Never invent live prices, news, or indicators
- If data missing, say DATA UNAVAILABLE

Trading Rules:
- Always use risk management warnings
- Never guarantee profits
- Use structured analysis
- Consider multi-timeframe when available

Memory:
- Remember user's preferred assets, timeframe, risk
- Keep memory isolated per user_id
"""

def clean_ai_response(text: str) -> str:
    if not text:
        return ""
    text = re.sub(r"<think>.*?</think>", "", text, flags=re.DOTALL | re.IGNORECASE)
    text = re.sub(r"<think>.*$", "", text, flags=re.DOTALL | re.IGNORECASE)
    text = re.sub(r"<\|.*?\|>", "", text)
    return text.strip()

class AIEngine:
    def __init__(self, memory=None):
        self.memory = memory
        # ElevenLabs client
        self.eleven_client = None
        if ELEVENLABS_API_KEY:
            try:
                from elevenlabs import ElevenLabs
                self.eleven_client = ElevenLabs(api_key=ELEVENLABS_API_KEY)
                logger.info("✅ ElevenLabs client initialized")
            except Exception as e:
                logger.warning(f"ElevenLabs init failed: {e}")

    def _get_provider_order(self) -> List[str]:
        order = []
        if AI_PROVIDER == "XAI" and XAI_API_KEY:
            order = ["xai", "groq", "gemini", "openai"]
        elif AI_PROVIDER == "GROQ" and GROQ_API_KEY:
            order = ["groq", "gemini", "openai", "xai"]
        elif AI_PROVIDER == "GEMINI" and GEMINI_API_KEY:
            order = ["gemini", "groq", "openai", "xai"]
        elif AI_PROVIDER == "OPENAI" and OPENAI_API_KEY:
            order = ["openai", "groq", "gemini", "xai"]
        else:
            # AUTO - prioritize based on available keys, XAI first if present as per original bot
            if XAI_API_KEY:
                order.append("xai")
            if GROQ_API_KEY:
                order.append("groq")
            if GEMINI_API_KEY:
                order.append("gemini")
            if OPENAI_API_KEY:
                order.append("openai")
            # Ensure at least groq/gemini/openai if no xai
            for p in ["groq", "gemini", "openai", "xai"]:
                if p not in order:
                    order.append(p)
        return order

    def _load_memory_history(self, user_id: str, limit: int = 20) -> List[dict]:
        if not self.memory:
            return []
        try:
            history = self.memory.get_history(user_id, limit=limit)
            # Convert to provider format later
            return history
        except Exception as e:
            logger.warning(f"Memory load failed for {user_id}: {e}")
            return []

    def _save_memory(self, user_id: str, prompt: str, response: str):
        if not self.memory:
            return
        try:
            self.memory.add_message(user_id, "user", prompt)
            self.memory.add_message(user_id, "assistant", response)
        except Exception as e:
            logger.warning(f"Memory save failed for {user_id}: {e}")

    def ask(self, user_id: str, prompt: str, image: Optional[Tuple[str, bytes]] = None) -> str:
        """
        Main entry: user_id for isolation, prompt, optional image=(mime_type, image_bytes)
        Returns str response
        """
        user_id = str(user_id)
        prompt = str(prompt or "").strip()
        if not prompt and not image:
            return "Please provide a question or image."

        # Load memory for context
        history = self._load_memory_history(user_id, limit=15)

        # Build provider order
        providers = self._get_provider_order()
        last_error = None

        for provider in providers:
            try:
                if provider == "xai" and XAI_API_KEY:
                    resp = self._xai(prompt, history, image)
                    if resp:
                        cleaned = clean_ai_response(resp)
                        self._save_memory(user_id, prompt, cleaned)
                        return cleaned
                elif provider == "groq" and GROQ_API_KEY:
                    resp = self._groq(prompt, history, image)
                    if resp:
                        cleaned = clean_ai_response(resp)
                        self._save_memory(user_id, prompt, cleaned)
                        return cleaned
                elif provider == "gemini" and GEMINI_API_KEY:
                    resp = self._gemini(prompt, history, image)
                    if resp:
                        cleaned = clean_ai_response(resp)
                        self._save_memory(user_id, prompt, cleaned)
                        return cleaned
                elif provider == "openai" and OPENAI_API_KEY:
                    resp = self._openai(prompt, history, image)
                    if resp:
                        cleaned = clean_ai_response(resp)
                        self._save_memory(user_id, prompt, cleaned)
                        return cleaned
            except Exception as e:
                last_error = e
                logger.warning(f"Provider {provider} failed: {e}")
                continue

        # If all fail
        error_msg = f"All AI providers failed. Last error: {last_error}" if last_error else "All AI providers failed - check API keys"
        logger.error(error_msg)
        raise RuntimeError("⚠️ AI Service Temporarily Unavailable. Please try again in a few seconds.")

    def _build_openai_messages(self, prompt: str, history: List[dict], image: Optional[Tuple[str, bytes]] = None, include_system: bool = True) -> List[dict]:
        messages = []
        if include_system:
            messages.append({"role": "system", "content": SYSTEM_PROMPT})
        # Add history
        for h in history[-10:]:  # last 10
            role = h.get("role", "user")
            content = h.get("content", "")
            if role in ["user", "assistant"] and content:
                messages.append({"role": role, "content": content})
        # Current prompt
        if image:
            mime, img_bytes = image
            b64 = base64.b64encode(img_bytes).decode("utf-8")
            messages.append({
                "role": "user",
                "content": [
                    {"type": "text", "text": prompt},
                    {"type": "image_url", "image_url": {"url": f"data:{mime};base64,{b64}"}}
                ]
            })
        else:
            messages.append({"role": "user", "content": prompt})
        return messages

    def _xai(self, prompt: str, history: List[dict], image: Optional[Tuple[str, bytes]]) -> Optional[str]:
        if not XAI_API_KEY:
            return None
        # xAI uses OpenAI compatible API
        model = XAI_MODEL
        if image:
            # xAI vision model - use grok-4 vision capable
            model = XAI_MODEL  # grok-4 supports vision
        messages = self._build_openai_messages(prompt, history, image)
        headers = {"Authorization": f"Bearer {XAI_API_KEY}", "Content-Type": "application/json"}
        payload = {"model": model, "messages": messages, "temperature": 0.7, "max_tokens": 2000}
        resp = requests.post(XAI_URL, headers=headers, json=payload, timeout=45)
        if resp.status_code == 429:
            raise RuntimeError("xAI rate limit")
        resp.raise_for_status()
        data = resp.json()
        return data["choices"][0]["message"]["content"]

    def _groq(self, prompt: str, history: List[dict], image: Optional[Tuple[str, bytes]]) -> Optional[str]:
        if not GROQ_API_KEY:
            return None
        model = GROQ_VISION_MODEL if image else GROQ_MODEL
        messages = self._build_openai_messages(prompt, history, image)
        headers = {"Authorization": f"Bearer {GROQ_API_KEY}", "Content-Type": "application/json"}
        payload = {"model": model, "messages": messages, "temperature": 0.7, "max_tokens": 2000}
        resp = requests.post(GROQ_URL, headers=headers, json=payload, timeout=45)
        if resp.status_code == 429:
            raise RuntimeError("Groq rate limit")
        resp.raise_for_status()
        data = resp.json()
        return data["choices"][0]["message"]["content"]

    def _openai(self, prompt: str, history: List[dict], image: Optional[Tuple[str, bytes]]) -> Optional[str]:
        if not OPENAI_API_KEY:
            return None
        model = OPENAI_MODEL
        # Use vision capable model if image and model is mini, it supports vision
        messages = self._build_openai_messages(prompt, history, image)
        headers = {"Authorization": f"Bearer {OPENAI_API_KEY}", "Content-Type": "application/json"}
        payload = {"model": model, "messages": messages, "temperature": 0.7, "max_tokens": 2000}
        url = OPENAI_URL
        # Support custom base URL
        if "openai.com" not in url:
            # If custom URL like https://api.openai.com/v1 or groq url, keep as is
            pass
        resp = requests.post(url, headers=headers, json=payload, timeout=45)
        resp.raise_for_status()
        data = resp.json()
        return data["choices"][0]["message"]["content"]

    def _gemini(self, prompt: str, history: List[dict], image: Optional[Tuple[str, bytes]]) -> Optional[str]:
        if not GEMINI_API_KEY:
            return None
        # Build Gemini format
        # history conversion
        contents = []
        # Add history
        for h in history[-8:]:
            role = h.get("role")
            content = h.get("content")
            if not content:
                continue
            # Gemini uses user/model roles
            g_role = "user" if role == "user" else "model"
            contents.append({"role": g_role, "parts": [{"text": content}]})

        # Current prompt with image
        if image:
            mime, img_bytes = image
            b64 = base64.b64encode(img_bytes).decode("utf-8")
            parts = [{"text": prompt}, {"inline_data": {"mime_type": mime, "data": b64}}]
            contents.append({"role": "user", "parts": parts})
        else:
            contents.append({"role": "user", "parts": [{"text": prompt}]})

        payload = {
            "contents": contents,
            "systemInstruction": {"parts": [{"text": SYSTEM_PROMPT}]},
            "generationConfig": {"temperature": 0.7, "maxOutputTokens": 2000}
        }
        url = GEMINI_URL.format(model=GEMINI_MODEL) + f"?key={GEMINI_API_KEY}"
        resp = requests.post(url, json=payload, timeout=45)
        resp.raise_for_status()
        data = resp.json()
        # Parse response
        try:
            candidates = data.get("candidates", [])
            if not candidates:
                return None
            parts = candidates[0].get("content", {}).get("parts", [])
            text = "".join(p.get("text","") for p in parts)
            return text
        except Exception as e:
            logger.warning(f"Gemini parse error: {e} - {data}")
            return None

    def generate_speech(self, text: str) -> io.BytesIO:
        """
        Generate speech via ElevenLabs
        Returns BytesIO
        """
        if not text:
            raise ValueError("Text empty")
        text = str(text).strip()[:800]  # limit
        if self.eleven_client and ELEVENLABS_API_KEY:
            try:
                audio = self.eleven_client.text_to_speech.convert(
                    voice_id=ELEVENLABS_VOICE_ID,
                    model_id=ELEVENLABS_MODEL_ID,
                    text=text,
                )
                # audio is iterator of bytes
                bio = io.BytesIO()
                for chunk in audio:
                    if chunk:
                        bio.write(chunk)
                bio.seek(0)
                bio.name = "voice.mp3"
                return bio
            except Exception as e:
                logger.warning(f"ElevenLabs TTS failed: {e}")
                # Fallback will be handled by caller edge_tts, but we try to still raise for fallback
                raise
        else:
            raise RuntimeError("ElevenLabs not configured")
