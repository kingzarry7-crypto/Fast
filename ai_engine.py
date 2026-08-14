import base64
import requests
import os
import re

# =====================================================
# ENVIRONMENT CONFIGURATION
# =====================================================
AI_PROVIDER = os.getenv("AI_PROVIDER", "AUTO").upper()

GROQ_API_KEY = os.getenv("GROQ_API_KEY")
GROQ_MODEL = os.getenv("GROQ_MODEL", "llama-3.3-70b-versatile")
GROQ_URL = "https://api.groq.com/openai/v1/chat/completions"

GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")
GEMINI_MODEL = os.getenv("GEMINI_MODEL", "gemini-3.7-flash")

OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")
OPENAI_MODEL = os.getenv("OPENAI_MODEL", "gpt-4o-mini")


class AIEngine:
    def __init__(self, memory=None):
        self.memory = memory

    # =====================================================
    # PUBLIC MAIN ENTRYPOINT (CALLED BY DISCORD / TELEGRAM)
    # =====================================================
    def ask(self, user_id: str, prompt: str, image=None) -> str:
        """
        Main public interface called by bots:
        ai.ask(user_id, prompt, image_tuple)
        """
        # 1. Fetch memory history if available
        history = []
        if self.memory and hasattr(self.memory, "get_history"):
            try:
                history = self.memory.get_history(user_id) or []
            except Exception as e:
                print(f"⚠️ Memory fetch warning: {e}")

        # 2. Build structured message list
        messages = []
        for msg in history:
            messages.append({
                "role": msg.get("role", "user"),
                "content": msg.get("content", "")
            })
        
        # Ensure input prompt is sanitized to avoid empty string errors
        clean_prompt = prompt or ""
        messages.append({
            "role": "user",
            "content": clean_prompt
        })

        # 3. Handle routing & fallbacks
        errors = []
        
        # Provider Order Execution
        providers = []
        if AI_PROVIDER == "GROQ":
            providers = [self._groq, self._gemini, self._openai]
        elif AI_PROVIDER == "GEMINI":
            providers = [self._gemini, self._groq, self._openai]
        elif AI_PROVIDER == "OPENAI":
            providers = [self._openai, self._groq, self._gemini]
        else:  # AUTO / DEFAULT
            providers = [self._groq, self._gemini, self._openai]

        for provider in providers:
            try:
                answer = provider(messages, image=image)
                
                # Save to memory on success
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
        
        prepared = []
        for message in messages:
            # Prevent Groq API string type validation errors on blank inputs
            content = message["content"] if message["content"] else " "
            prepared.append({
                "role": message["role"],
                "content": content
            })
            
        # Add image handling (OpenAI-compatible format)
        if image:
            mime_type, image_bytes = image
            encoded = base64.b64encode(image_bytes).decode("utf-8")
            data_url = f"data:{mime_type};base64,{encoded}"
            prepared.append({
                "role": "user",
                "content": [
                    {
                        "type": "text",
                        "text": "Analyze the attached image carefully and answer directly."
                    },
                    {
                        "type": "image_url",
                        "image_url": {"url": data_url}
                    }
                ]
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
            try:
                error = response.json()
            except Exception:
                error = response.text
            raise RuntimeError(f"Groq API error: {error}")
            
        data = response.json()
        choices = data.get("choices", [])
        
        if not choices:
            raise RuntimeError("Groq returned no choices.")
            
        answer = choices[0].get("message", {}).get("content", "")
        
        if not answer:
            raise RuntimeError("Groq returned no text.")
            
        return self._clean_response(answer)

    # =====================================================
    # GEMINI FALLBACK
    # =====================================================
    def _gemini(self, messages, image=None):
        if not GEMINI_API_KEY:
            raise RuntimeError("GEMINI_API_KEY is not configured.")
        
        url = f"https://generativelanguage.googleapis.com/v1beta/models/{GEMINI_MODEL}:generateContent?key={GEMINI_API_KEY}"
        
        contents = []
        for msg in messages:
            role = "user" if msg["role"] == "user" else "model"
            text_content = msg["content"] if msg["content"] else " "
            contents.append({
                "role": role,
                "parts": [{"text": text_content}]
            })

        if image:
            mime_type, image_bytes = image
            encoded = base64.b64encode(image_bytes).decode("utf-8")
            contents.append({
                "role": "user",
                "parts": [
                    {"inline_data": {"mime_type": mime_type, "data": encoded}},
                    {"text": "Analyze this image carefully."}
                ]
            })

        payload = {"contents": contents}
        response = requests.post(url, json=payload, timeout=120)

        if response.status_code != 200:
            raise RuntimeError(f"Gemini API error: {response.text}")

        data = response.json()
        try:
            answer = data["candidates"][0]["content"]["parts"][0]["text"]
            return self._clean_response(answer)
        except (KeyError, IndexError):
            raise RuntimeError("Gemini returned invalid structure.")

    # =====================================================
    # OPENAI FALLBACK
    # =====================================================
    def _openai(self, messages, image=None):
        if not OPENAI_API_KEY:
            raise RuntimeError("OPENAI_API_KEY is not configured.")

        url = "https://api.openai.com/v1/chat/completions"
        prepared = [{"role": m["role"], "content": m["content"] or " "} for m in messages]

        if image:
            mime_type, image_bytes = image
            encoded = base64.b64encode(image_bytes).decode("utf-8")
            prepared.append({
                "role": "user",
                "content": [
                    {"type": "text", "text": "Analyze this image carefully."},
                    {"type": "image_url", "image_url": {"url": f"data:{mime_type};base64,{encoded}"}}
                ]
            })

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

    # =====================================================
    # HELPERS
    # =====================================================
    def _clean_response(self, text: str) -> str:
        """Cleans up internal AI formatting artifacts."""
        if not text:
            return ""
        # Strip trailing system markers if any
        text = re.sub(r"<\|.*?\|>", "", text)
        return text.strip()
