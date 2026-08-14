import base64
import io
import os
import re
import time
import requests
from dotenv import load_dotenv

# Try importing ElevenLabs SDK safely
try:
    from elevenlabs.client import ElevenLabs
    HAS_ELEVENLABS = True
except ImportError:
    HAS_ELEVENLABS = False

# Load environment variables
load_dotenv()

# =====================================================
# ENVIRONMENT CONFIGURATION
# =====================================================
AI_PROVIDER = os.getenv("AI_PROVIDER", "AUTO").upper()

GROQ_API_KEY = os.getenv("GROQ_API_KEY")
GROQ_MODEL = os.getenv("GROQ_MODEL", "qwen/qwen3.6-27b")
GROQ_URL = "https://api.groq.com/openai/v1/chat/completions"

GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")
GEMINI_MODEL = os.getenv("GEMINI_MODEL", "gemini-3.7-flash")
GEMINI_BACKUP_MODEL = os.getenv("GEMINI_BACKUP_MODEL", "gemini-2.5-flash")

OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")
OPENAI_MODEL = os.getenv("OPENAI_MODEL", "gpt-4o-mini")

# ElevenLabs Configuration
ELEVENLABS_API_KEY = os.getenv("ELEVENLABS_API_KEY")
ELEVENLABS_MODEL_ID = os.getenv("ELEVENLABS_MODEL_ID", "eleven_flash_v2_5")
ELEVENLABS_VOICE_ID = os.getenv("ELEVENLABS_VOICE_ID", "21m00Tcm4TlvDq8ikWAM")

# System Prompts
DEFAULT_SYSTEM_PROMPT = (
    "You are King Zarry AI, an advanced multi-platform assistant with text, vision, and voice capabilities. "
    "You have native ElevenLabs speech output integration enabled across Discord and Telegram. "
    "If a user asks about voice features or requests audio, answer enthusiastically and concisely!"
)

SYSTEM_VISION_PROMPT = (
    "You are King Zarry AI analyzing an image. Answer the user's "
    "question directly. Do NOT output internal reasoning, chain-of-thought, or <think> tags."
)


class AIEngine:

    def __init__(self, memory=None):
        self.memory = memory
        self.eleven_client = (
            ElevenLabs(api_key=ELEVENLABS_API_KEY)
            if (HAS_ELEVENLABS and ELEVENLABS_API_KEY)
            else None
        )

    def ask(self, user_id: str, prompt: str, image=None) -> str:
        history = []
        if self.memory and hasattr(self.memory, "get_history"):
            try:
                history = self.memory.get_history(user_id) or []
            except Exception as e:
                print(f"⚠️ Memory fetch warning: {e}")

        messages = []
        
        # Inject core system prompt
        messages.append({"role": "system", "content": DEFAULT_SYSTEM_PROMPT})

        # Append historical messages
        for msg in history:
            role = msg.get("role", "user")
            content = msg.get("content", "")
            if content and role in ["user", "assistant", "system"]:
                messages.append({"role": role, "content": content})

        clean_prompt = prompt or ""
        messages.append({"role": "user", "content": clean_prompt})

        errors = []

        if AI_PROVIDER == "GROQ":
            providers = [self._groq, self._gemini, self._openai]
        elif AI_PROVIDER == "GEMINI":
            providers = [self._gemini, self._groq, self._openai]
        elif AI_PROVIDER == "OPENAI":
            providers = [self._openai, self._groq, self._gemini]
        else:
            providers = [self._groq, self._gemini, self._openai]

        for provider in providers:
            try:
                answer = provider(messages, image=image)

                if answer and self.memory and hasattr(self.memory, "add"):
                    try:
                        self.memory.add(user_id, "user", clean_prompt)
                        self.memory.add(user_id, "assistant", answer)
                    except Exception as mem_err:
                        print(f"⚠️ Memory save warning: {mem_err}")

                if answer:
                    return answer
            except Exception as err:
                errors.append(f"{provider.__name__}: {str(err)}")
                continue

        raise RuntimeError(
            "All configured AI providers failed. " + " | ".join(errors)
        )

    # =====================================================
    # ELEVENLABS VOICE GENERATION
    # =====================================================
    def generate_speech(self, text: str) -> io.BytesIO:
        """Converts text to audio bytes using ElevenLabs API (eleven_flash_v2_5)."""
        if not self.eleven_client:
            raise RuntimeError(
                "ElevenLabs is not configured. Ensure ELEVENLABS_API_KEY is set and 'elevenlabs' package is installed."
            )

        audio_generator = self.eleven_client.text_to_speech.convert(
            text=text,
            voice_id=ELEVENLABS_VOICE_ID,
            model_id=ELEVENLABS_MODEL_ID,
            output_format="mp3_44100_128",
        )
        audio_bytes = b"".join(audio_generator)
        return io.BytesIO(audio_bytes)

    # =====================================================
    # GROQ PROVIDER
    # =====================================================
    def _groq(self, messages, image=None):
        if not GROQ_API_KEY:
            raise RuntimeError("GROQ_API_KEY is not configured.")

        prepared = []
        for message in messages:
            content = message["content"] if message["content"] else " "
            prepared.append({"role": message["role"], "content": content})

        if image:
            # Override/append system prompt for vision
            prepared.insert(0, {"role": "system", "content": SYSTEM_VISION_PROMPT})

            mime_type, image_bytes = image
            encoded = base64.b64encode(image_bytes).decode("utf-8")
            data_url = f"data:{mime_type};base64,{encoded}"

            last_text = prepared[-1]["content"]
            prepared[-1]["content"] = [
                {"type": "text", "text": last_text},
                {"type": "image_url", "image_url": {"url": data_url}},
            ]

        payload = {
            "model": GROQ_MODEL,
            "messages": prepared,
            "temperature": 0.2,
            "max_tokens": 1500,
        }

        # Include reasoning_format for Qwen / DeepSeek models if supported
        if "qwen" in GROQ_MODEL.lower() or "deepseek" in GROQ_MODEL.lower():
            payload["reasoning_format"] = "hidden"

        response = requests.post(
            GROQ_URL,
            headers={
                "Authorization": f"Bearer {GROQ_API_KEY}",
                "Content-Type": "application/json",
            },
            json=payload,
            timeout=120,
        )

        if response.status_code != 200:
            raise RuntimeError(f"Groq API error: {response.text}")

        data = response.json()
        choices = data.get("choices", [])
        if not choices:
            raise RuntimeError("Groq returned no choices.")

        answer = choices[0].get("message", {}).get("content", "")
        return self._clean_response(answer)

    # =====================================================
    # GEMINI PROVIDER
    # =====================================================
    def _gemini(self, messages, image=None):
        if not GEMINI_API_KEY:
            raise RuntimeError("GEMINI_API_KEY is not configured.")

        contents = []
        system_instruction = None

        for msg in messages:
            if msg["role"] == "system":
                system_instruction = {"parts": [{"text": msg["content"]}]}
                continue

            role = "model" if msg["role"] in ["assistant", "model"] else "user"
            text_content = msg["content"] if msg["content"] else " "
            contents.append({"role": role, "parts": [{"text": text_content}]})

        if not contents:
            contents.append({"role": "user", "parts": [{"text": "Hello"}]})

        if image and contents:
            mime_type, image_bytes = image
            encoded = base64.b64encode(image_bytes).decode("utf-8")

            current_prompt = contents[-1]["parts"][0]["text"]
            contents[-1]["parts"][0]["text"] = f"{SYSTEM_VISION_PROMPT}\n\nUser Question: {current_prompt}"

            contents[-1]["parts"].insert(
                0, {"inline_data": {"mime_type": mime_type, "data": encoded}}
            )

        payload = {
            "contents": contents,
            "generationConfig": {"maxOutputTokens": 1500}
        }

        if system_instruction:
            payload["systemInstruction"] = system_instruction

        models_to_try = [GEMINI_MODEL, GEMINI_BACKUP_MODEL]
        last_error = ""

        for model_name in models_to_try:
            url = f"https://generativelanguage.googleapis.com/v1beta/models/{model_name}:generateContent?key={GEMINI_API_KEY}"

            for attempt in range(2):
                response = requests.post(url, json=payload, timeout=120)

                if response.status_code == 200:
                    data = response.json()
                    try:
                        answer = data["candidates"][0]["content"]["parts"][0]["text"]
                        return self._clean_response(answer)
                    except (KeyError, IndexError):
                        raise RuntimeError("Gemini returned invalid structure.")

                elif response.status_code == 503 and attempt == 0:
                    time.sleep(1)
                    continue
                else:
                    last_error = response.text
                    break

        raise RuntimeError(f"Gemini API error: {last_error}")

    # =====================================================
    # OPENAI PROVIDER
    # =====================================================
    def _openai(self, messages, image=None):
        if not OPENAI_API_KEY:
            raise RuntimeError("OPENAI_API_KEY is not configured.")

        url = "https://api.openai.com/v1/chat/completions"
        prepared = []

        for m in messages:
            prepared.append({"role": m["role"], "content": m["content"] or " "})

        if image:
            prepared.insert(0, {"role": "system", "content": SYSTEM_VISION_PROMPT})
            mime_type, image_bytes = image
            encoded = base64.b64encode(image_bytes).decode("utf-8")
            prepared[-1]["content"] = [
                {"type": "text", "text": prepared[-1]["content"]},
                {
                    "type": "image_url",
                    "image_url": {"url": f"data:{mime_type};base64,{encoded}"},
                },
            ]

        payload = {
            "model": OPENAI_MODEL,
            "messages": prepared,
            "max_tokens": 1500,
        }

        response = requests.post(
            url,
            headers={
                "Authorization": f"Bearer {OPENAI_API_KEY}",
                "Content-Type": "application/json",
            },
            json=payload,
            timeout=120,
        )

        if response.status_code != 200:
            raise RuntimeError(f"OpenAI API error: {response.text}")

        data = response.json()
        answer = data["choices"][0]["message"]["content"]
        return self._clean_response(answer)

    # =====================================================
    # RESPONSE CLEANER
    # =====================================================
    def _clean_response(self, text: str) -> str:
        if not text:
            return ""

        # 1. Remove complete <think>...</think> blocks
        text = re.sub(r"<think>.*?</think>", "", text, flags=re.DOTALL | re.IGNORECASE)

        # 2. Remove unclosed <think> blocks (truncated reasoning outputs)
        text = re.sub(r"<think>.*$", "", text, flags=re.DOTALL | re.IGNORECASE)

        # 3. Strip special model control tokens
        text = re.sub(r"<\|.*?\|>", "", text)

        return text.strip()
