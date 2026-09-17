import os

import httpx


def clean_env_str(value, default=None):
    if value is None:
        return default
    value = str(value).strip()
    return value or default


OPENROUTER_API_KEY = clean_env_str(os.getenv("OPENROUTER_API_KEY"))
OPENROUTER_BASE_URL = clean_env_str(
    os.getenv("OPENROUTER_BASE_URL"),
    "https://openrouter.ai/api/v1",
)
OPENROUTER_MODEL = clean_env_str(
    os.getenv("OPENROUTER_MODEL"),
    "openrouter/free",
)

# Compatibility aliases for existing code.
OPENAI_API_KEY = OPENROUTER_API_KEY
OPENAI_URL = f"{OPENROUTER_BASE_URL}/chat/completions"
OPENAI_MODEL = OPENROUTER_MODEL


class AIEngine:
    def __init__(self, *args, **kwargs):
        self.api_key = OPENROUTER_API_KEY
        self.url = OPENAI_URL
        self.model = OPENROUTER_MODEL

    async def generate_response(self, prompt, system_prompt=None, messages=None, **kwargs):
        if messages is None:
            messages = []
        if not messages:
            if system_prompt:
                messages.append({"role": "system", "content": system_prompt})
            messages.append({"role": "user", "content": str(prompt)})

        if not self.api_key:
            return "AI provider is not configured. Add OPENROUTER_API_KEY in Railway."

        payload = {
            "model": self.model,
            "messages": messages,
        }
        for key in ("temperature", "max_tokens", "top_p"):
            if key in kwargs and kwargs[key] is not None:
                payload[key] = kwargs[key]

        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json",
            "HTTP-Referer": "https://github.com/kingzarry7-crypto/Fast",
            "X-Title": "King Zarry AI",
        }

        async with httpx.AsyncClient(timeout=60) as client:
            response = await client.post(self.url, headers=headers, json=payload)
            response.raise_for_status()
            data = response.json()

        choices = data.get("choices") or []
        if not choices:
            return "The AI provider returned no response."
        message = choices[0].get("message") or {}
        return message.get("content") or "The AI provider returned an empty response."

    async def ask(self, prompt, **kwargs):
        return await self.generate_response(prompt, **kwargs)
