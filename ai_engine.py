import base64
import requests
import os
import re
import time

# =====================================================
# ENVIRONMENT CONFIGURATION
# =====================================================
AI_PROVIDER = os.getenv("AI_PROVIDER", "AUTO").upper()

GROQ_API_KEY = os.getenv("GROQ_API_KEY")
GROQ_MODEL = os.getenv("GROQ_MODEL", "llama-3.3-70b-versatile")
GROQ_URL = "https://api.groq.com/openai/v1/chat/completions"

GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")
GEMINI_MODEL = os.getenv("GEMINI_MODEL", "gemini-3.7-flash")
GEMINI_BACKUP_MODEL = os.getenv("GEMINI_BACKUP_MODEL", "gemini-2.5-flash")

OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")
OPENAI_MODEL = os.getenv("OPENAI_MODEL", "gpt-4o-mini")


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
            messages.append({
                "role": msg.get("role", "user"),
                "content": msg.get("content", "")
            })
        
        clean_prompt = prompt or ""
        messages.append({
            "role": "user",
            "content": clean_prompt
        })

        errors = []
        
        # When image is present, prioritize Gemini/OpenAI vision capabilities
        if image:
            providers = [self._gemini, self._openai, self._groq]
        elif AI_PROVIDER == "GROQ":
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
                
                if self.memory and hasattr(self.memory, "add"):
                    try:
                        self.memory.add(user_id, "user", clean_prompt)
                        self.memory.add(user_id, "assistant", answer)
                    except Exception as mem_err:
                        print(f"⚠️ Memory save warning: {mem_err}")
                        
                return answer
            except Exception as err:
                errors.append(f"{provider.__name__}: {str(err)}")
                continue

        raise RuntimeError("All configured AI providers failed. " + " | ".join(errors))

    # =====================================================
    # GROQ PROVIDER
    # =====================================================
    def _groq(self, messages, image=None):
        if not GROQ_API_KEY:
            raise RuntimeError("GROQ_API_KEY is not configured.")
        
        # If image is provided and model is non-vision, skip Groq to allow Gemini/OpenAI vision to run
        if image and "vision" not in GROQ_MODEL.lower():
            raise RuntimeError(f"Groq model '{GROQ_MODEL}' does not support vision inputs.")

        prepared = []
        for message in messages:
            content = message["content"] if message["content"] else " "
            prepared.append({
                "role": message["role"],
                "content": content
            })

        payload = {
            "model": GROQ_MODEL,
            "messages": prepared,
            "temperature": 0.3,
            "max_tokens": 700
        }
        
        response = requests.post(
            GROQ_URL,
            headers={
                "Authorization": f"Bearer {GROQ_API_KEY}",
                "Content-Type": "application/json"
            },
            json=payload,
            timeout=120
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
    # GEMINI PROVIDER (WITH 503 RETRY & BACKUP MODEL)
    # =====================================================
    def _gemini(self, messages, image=None):
        if not GEMINI_API_KEY:
            raise RuntimeError("GEMINI_API_KEY is not configured.")
        
        contents = []
        for msg in messages:
            role = "user" if msg["role"] == "user" else "model"
            text_content = msg["content"] if msg["content"] else " "
            contents.append({
                "role": role,
                "parts": [{"text": text_content}]
            })

        # Merge image into the last user turn (prevents Gemini 400 bad request)
        if image and contents:
            mime_type, image_bytes = image
            encoded = base64.b64encode(image_bytes).decode("utf-8")
            contents[-1]["parts"].insert(0, {
                "inline_data": {
                    "mime_type": mime_type,
                    "data": encoded
                }
            })

        payload = {"contents": contents}

        # Try Primary Model then Backup Model if 503/High Demand occurs
        models_to_try = [GEMINI_MODEL, GEMINI_BACKUP_MODEL]

        for model_name in models_to_try:
            url = f"https://generativelanguage.googleapis.com/v1beta/models/{model_name}:generateContent?key={GEMINI_API_KEY}"
            
            # Retry loop for temporary 503 unavailable status
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
                    time.sleep(1)  # Brief pause before retry
                    continue
                else:
                    break  # Try next backup model

        raise RuntimeError(f"Gemini API error: {response.text}")

    # =====================================================
    # OPENAI PROVIDER
    # =====================================================
    def _openai(self, messages, image=None):
        if not OPENAI_API_KEY:
            raise RuntimeError("OPENAI_API_KEY is not configured.")

        url = "https://api.openai.com/v1/chat/completions"
        prepared = [{"role": m["role"], "content": m["content"] or " "} for m in messages]

        if image:
            mime_type, image_bytes = image
            encoded = base64.b64encode(image_bytes).decode("utf-8")
            prepared[-1]["content"] = [
                {"type": "text", "text": prepared[-1]["content"]},
                {"type": "image_url", "image_url": {"url": f"data:{mime_type};base64,{encoded}"}}
            ]

        payload = {
            "model": OPENAI_MODEL,
            "messages": prepared,
            "max_tokens": 700
        }
        
        response = requests.post(
            url,
            headers={"Authorization": f"Bearer {OPENAI_API_KEY}"},
            json=payload,
            timeout=120
        )

        if response.status_code != 200:
            raise RuntimeError(f"OpenAI API error: {response.text}")

        data = response.json()
        answer = data["choices"][0]["message"]["content"]
        return self._clean_response(answer)

    def _clean_response(self, text: str) -> str:
        if not text:
            return ""
        text = re.sub(r"<\|.*?\|>", "", text)
        return text.strip()
