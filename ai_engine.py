import base64
import copy
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
GROQ_MODEL = os.getenv("GROQ_MODEL", "llama-3.3-70b-versatile")
GROQ_VISION_MODEL = os.getenv("GROQ_VISION_MODEL", "llama-3.2-11b-vision-preview")
GROQ_URL = "https://api.groq.com/openai/v1/chat/completions"

GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")
GEMINI_MODEL = os.getenv("GEMINI_MODEL", "gemini-1.5-flash")
GEMINI_BACKUP_MODEL = os.getenv("GEMINI_BACKUP_MODEL", "gemini-1.5-pro")

OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")
OPENAI_MODEL = os.getenv("OPENAI_MODEL", "gpt-4o-mini")

# ElevenLabs Configuration
ELEVENLABS_API_KEY = os.getenv("ELEVENLABS_API_KEY")
ELEVENLABS_MODEL_ID = os.getenv("ELEVENLABS_MODEL_ID", "eleven_flash_v2_5")
ELEVENLABS_VOICE_ID = os.getenv("ELEVENLABS_VOICE_ID", "21m00Tcm4TlvDq8ikWAM")

# System Prompts
DEFAULT_SYSTEM_PROMPT = (
    "You are King Zarry AI, an advanced multi-platform assistant with text, vision, and market analysis capabilities. "
    "Keep responses concise, clear, and direct. "
    "NEVER mention ElevenLabs, Discord, Telegram, or any underlying tools, models, or APIs. "
    "If the user asks if you can speak, talk, or send voice messages, respond naturally with: "
    "'Yes, I can talk to you! What would you like me to say?'"
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
                raw_history = self.memory.get_history(user_id) or []
                # Filter memory to valid user/assistant messages only
                for msg in raw_history:
                    if isinstance(msg, dict):
                        role = msg.get("role", "user")
                        content = msg.get("content", "")
                        if content and role in ["user", "assistant"]:
                            history.append({"role": role, "content": content})
            except Exception as e:
                print(f"⚠️ Memory fetch warning: {e}")

        messages = []
        
        # Inject core system prompt
        messages.append({"role": "system", "content": DEFAULT_SYSTEM_PROMPT})

        # Append historical chat messages
        messages.extend(history)

        clean_prompt = (prompt or "").strip()
        
        # Determine prompt text for messages list
        if not clean_prompt and image:
            user_msg_content = "Analyze this image."
        else:
            user_msg_content = clean_prompt or "Hello"

        messages.append({"role": "user", "content": user_msg_content})

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
                # Pass a deepcopy to avoid provider state contamination during fallback retries
                answer = provider(copy.deepcopy(messages), image=image)

                if answer and self.memory and hasattr(self.memory, "add"):
                    try:
                        # Prepare descriptive memory text for user query
                        if image:
                            saved_user_prompt = f"[Image] {clean_prompt}".strip() if clean_prompt else "[Image sent]"
                        else:
                            saved_user_prompt = clean_prompt

                        self.memory.add(user_id, "user", saved_user_prompt)
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
        selected_model = GROQ_VISION_MODEL if image else GROQ_MODEL

        for message in messages:
            content = message.get("content") or " "
            prepared.append({"role": message["role"], "content": content})

        if image:
            # Replace system prompt with vision-specific prompt
            prepared = [m for m in prepared if m["role"] != "system"]
            prepared.insert(0, {"role": "system", "content": SYSTEM_VISION_PROMPT})

            mime_type, image_bytes = image
            encoded = base64.b64encode(image_bytes).decode("utf-8")
            data_url = f"data:{mime_type};base64,{encoded}"

            last_text = prepared[-1]["content"] if isinstance(prepared[-1]["content"], str) else ""
            prepared[-1]["content"] = [
                {"type": "text", "text": last_text or "Analyze this image."},
                {"type": "image_url", "image_url": {"url": data_url}},
            ]

        payload = {
            "model": selected_model,
            "messages": prepared,
            "temperature": 0.2,
            "max_tokens": 1500,
        }

        if "qwen" in selected_model.lower() or "deepseek" in selected_model.lower():
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
            raise RuntimeError(f"Groq API error ({response.status_code}): {response.text}")

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

        active_system_prompt = SYSTEM_VISION_PROMPT if image else DEFAULT_SYSTEM_PROMPT
        system_instruction = {"parts": [{"text": active_system_prompt}]}

        # Properly format history into back-and-forth turn sequences required by Gemini
        contents = self._format_gemini_contents(messages, image=image)

        payload = {
            "contents": contents,
            "systemInstruction": system_instruction,
            "generationConfig": {"maxOutputTokens": 1500}
        }

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

    def _format_gemini_contents(self, messages, image=None):
        contents = []
        for msg in messages:
            if msg.get("role") == "system":
                continue

            role = "model" if msg.get("role") in ["assistant", "model"] else "user"
            text_content = msg.get("content") or " "
            
            # Avoid adjacent duplicate roles in Gemini history payload
            if contents and contents[-1]["role"] == role:
                contents[-1]["parts"].append({"text": text_content})
            else:
                contents.append({"role": role, "parts": [{"text": text_content}]})

        # Ensure history starts with user role
        if contents and contents[0]["role"] == "model":
            contents.pop(0)

        if not contents:
            contents.append({"role": "user", "parts": [{"text": "Hello"}]})

        # Attach image to the latest user message
        if image and contents:
            mime_type, image_bytes = image
            encoded = base64.b64encode(image_bytes).decode("utf-8")
            
            # Make sure target turn is 'user'
            if contents[-1]["role"] != "user":
                contents.append({"role": "user", "parts": [{"text": "Analyze this image."}]})

            contents[-1]["parts"].insert(
                0, {"inline_data": {"mime_type": mime_type, "data": encoded}}
            )

        return contents

    # =====================================================
    # OPENAI PROVIDER
    # =====================================================
    def _openai(self, messages, image=None):
        if not OPENAI_API_KEY:
            raise RuntimeError("OPENAI_API_KEY is not configured.")

        url = "https://api.openai.com/v1/chat/completions"
        prepared = []

        for m in messages:
            content = m.get("content") or " "
            prepared.append({"role": m["role"], "content": content})

        if image:
            prepared = [m for m in prepared if m["role"] != "system"]
            prepared.insert(0, {"role": "system", "content": SYSTEM_VISION_PROMPT})
            
            mime_type, image_bytes = image
            encoded = base64.b64encode(image_bytes).decode("utf-8")
            last_text = prepared[-1]["content"] if isinstance(prepared[-1]["content"], str) else ""

            prepared[-1]["content"] = [
                {"type": "text", "text": last_text or "Analyze this image."},
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
            raise RuntimeError(f"OpenAI API error ({response.status_code}): {response.text}")

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

        # 2. Remove unclosed <think> blocks
        text = re.sub(r"<think>.*$", "", text, flags=re.DOTALL | re.IGNORECASE)

        # 3. Strip special model control tokens
        text = re.sub(r"<\|.*?\|>", "", text)

        return text.strip()
