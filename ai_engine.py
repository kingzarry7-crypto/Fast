import base64
import os
import re
import time
import requests

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

SYSTEM_VISION_PROMPT = (
    "You are a helpful AI assistant. When analyzing images, answer the user's "
    "question directly. Do NOT output internal reasoning, chain-of-thought, or <think> tags."
)


class AIEngine:

    def __init__(self, memory=None):
        self.memory = memory

    def ask(self, user_id: str, prompt: str, image=None) -> str:
        history = []
        if self.memory and hasattr(self.memory, "get_history"):
            try:
                history = self.memory.get_history(user_id) or []
            except Exception as e:
                print(f"⚠️ Memory fetch warning: {e}")

        messages = []
        for msg in history:
            messages.append(
                {"role": msg.get("role", "user"), "content": msg.get("content", "")}
            )

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
    # GROQ PROVIDER
    # =====================================================
    def _groq(self, messages, image=None):
        if not GROQ_API_KEY:
            raise RuntimeError("GROQ_API_KEY is not configured.")

        prepared = []
        if image:
            prepared.append({"role": "system", "content": SYSTEM_VISION_PROMPT})

        for message in messages:
            content = message["content"] if message["content"] else " "
            prepared.append({"role": message["role"], "content": content})

        if image and prepared:
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
            # Disable extra thinking outputs where supported
            "reasoning_format": "hidden" 
        }

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
        for msg in messages:
            role = "user" if msg["role"] == "user" else "model"
            text_content = msg["content"] if msg["content"] else " "
            contents.append({"role": role, "parts": [{"text": text_content}]})

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

        models_to_try = [GEMINI_MODEL, GEMINI_BACKUP_MODEL]

        for model_name in models_to_try:
            url = f"https://generativelanguage.googleapis.com/v1beta/models/{model_name}:generateContent?key={GEMINI_API_KEY}"

            for attempt in range(2):
                response = requests.post(url, json=payload, timeout=120)

                if response.status_code == 200:
                    data = response.json()
                    try:
                        answer = data["candidates"][0]["content"]["parts"][0][
                            "text"
                        ]
                        return self._clean_response(answer)
                    except (KeyError, IndexError):
                        raise RuntimeError("Gemini returned invalid structure.")

                elif response.status_code == 503 and attempt == 0:
                    time.sleep(1)
                    continue
                else:
                    break

        raise RuntimeError(f"Gemini API error: {response.text}")

    # =====================================================
    # OPENAI PROVIDER
    # =====================================================
    def _openai(self, messages, image=None):
        if not OPENAI_API_KEY:
            raise RuntimeError("OPENAI_API_KEY is not configured.")

        url = "https://api.openai.com/v1/chat/completions"
        prepared = []

        if image:
            prepared.append({"role": "system", "content": SYSTEM_VISION_PROMPT})

        for m in messages:
            prepared.append({"role": m["role"], "content": m["content"] or " "})

        if image:
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
            headers={"Authorization": f"Bearer {OPENAI_API_KEY}"},
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
        text = re.sub(r"<think>.*?</think>", "", text, flags=re.DOTALL)

        # 2. If <think> was opened but never closed (truncated reasoning output),
        # extract text that comes AFTER the last tag, or strip out the whole think block
        if "<think>" in text:
            parts = text.split("<think>")
            # If there's text before or after, keep non-thinking parts
            text = "".join([p for p in parts if not p.strip().startswith("The user") and not p.strip().startswith("1.")])

        # 3. Strip model control tokens
        text = re.sub(r"<\|.*?\|>", "", text)
        
        return text.strip()
