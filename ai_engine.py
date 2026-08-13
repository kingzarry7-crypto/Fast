import base64
import requests

from config import (
    GEMINI_API_KEY,
    OPENAI_API_KEY,
    AI_PROVIDER,
    GEMINI_MODEL,
    OPENAI_MODEL,
    GEMINI_URL,
    OPENAI_URL
)


# =========================================================
# KING ZARRY AI 👑
# AI ENGINE
# =========================================================

SYSTEM_PROMPT = """
You are King Zarry AI 👑.

You are the official AI assistant for the King Zarry community.

You can help with:

• Cryptocurrency
• Bitcoin
• Ethereum
• Solana
• Forex
• Gold / XAUUSD
• Trading
• Technical analysis
• Risk management
• Programming
• Artificial intelligence
• Technology
• Business
• Education
• General questions
• Casual conversation

TRADING RULES:

Never guarantee profit.

Never claim certainty about future market movement.

Clearly distinguish between:

CONFIRMED
PROBABLE
UNCERTAIN

When discussing a trading setup, explain:

• Direction
• Market structure
• Entry area
• Stop / invalidation
• Take profits
• Risk / reward
• Reasoning

Never pretend to have live market data.

Only analyze live prices when live market data has actually been supplied.

Be practical, clear and concise.

Use emojis naturally.

You are King Zarry AI 👑.
"""


class AIEngine:

    def __init__(self, memory):

        self.memory = memory

    # =====================================================
    # GEMINI
    # =====================================================

    def _gemini(
        self,
        messages,
        image=None
    ):

        if not GEMINI_API_KEY:

            raise RuntimeError(
                "GEMINI_API_KEY is not configured."
            )

        parts = []

        for message in messages:

            role = message.get("role")
            content = message.get(
                "content",
                ""
            )

            if role == "system":
                continue

            parts.append({
                "text": str(content)
            })

        if image:

            mime_type, image_bytes = image

            encoded = base64.b64encode(
                image_bytes
            ).decode("utf-8")

            parts.append({

                "inline_data": {

                    "mime_type": mime_type,

                    "data": encoded
                }

            })

        payload = {

            "systemInstruction": {

                "parts": [

                    {
                        "text": SYSTEM_PROMPT
                    }

                ]

            },

            "contents": [

                {

                    "role": "user",

                    "parts": parts

                }

            ],

            "generationConfig": {

                "temperature": 0.3,

                "maxOutputTokens": 1500

            }

        }

        url = (
            f"{GEMINI_URL}/"
            f"{GEMINI_MODEL}:generateContent"
        )

        response = requests.post(

            url,

            headers={

                "x-goog-api-key":
                    GEMINI_API_KEY,

                "Content-Type":
                    "application/json"

            },

            json=payload,

            timeout=120

        )

        if response.status_code != 200:

            try:
                error = response.json()

            except Exception:
                error = response.text

            raise RuntimeError(
                f"Gemini API error: {error}"
            )

        data = response.json()

        text_parts = []

        for candidate in data.get(
            "candidates",
            []
        ):

            content = candidate.get(
                "content",
                {}
            )

            for part in content.get(
                "parts",
                []
            ):

                if "text" in part:

                    text_parts.append(
                        part["text"]
                    )

        answer = "\n".join(
            text_parts
        ).strip()

        if not answer:

            raise RuntimeError(
                "Gemini returned no text."
            )

        return answer

    # =====================================================
    # OPENAI
    # =====================================================

    def _openai(
        self,
        messages,
        image=None
    ):

        if not OPENAI_API_KEY:

            raise RuntimeError(
                "OPENAI_API_KEY is not configured."
            )

        prepared = []

        for message in messages:

            prepared.append({

                "role":
                    message["role"],

                "content":
                    message["content"]

            })

        if image:

            mime_type, image_bytes = image

            encoded = base64.b64encode(
                image_bytes
            ).decode("utf-8")

            data_url = (
                f"data:{mime_type};base64,"
                f"{encoded}"
            )

            prepared.append({

                "role": "user",

                "content": [

                    {

                        "type": "text",

                        "text":
                            "Analyze the attached image carefully."

                    },

                    {

                        "type": "image_url",

                        "image_url": {

                            "url":
                                data_url,

                            "detail":
                                "high"

                        }

                    }

                ]

            })

        payload = {

            "model":
                OPENAI_MODEL,

            "messages":
                prepared,

            "temperature":
                0.3,

            "max_tokens":
                1500

        }

        response = requests.post(

            OPENAI_URL,

            headers={

                "Authorization":
                    f"Bearer {OPENAI_API_KEY}",

                "Content-Type":
                    "application/json"

            },

            json=payload,

            timeout=120

        )

        if response.status_code != 200:

            try:
                error = response.json()

            except Exception:
                error = response.text

            raise RuntimeError(
                f"OpenAI API error: {error}"
            )

        data = response.json()

        answer = (
            data["choices"][0]
            ["message"]["content"]
        )

        if not answer:

            raise RuntimeError(
                "OpenAI returned no text."
            )

        return answer.strip()

    # =====================================================
    # ASK AI
    # =====================================================

    def ask(
        self,
        user_id,
        prompt,
        image=None
    ):

        user_id = str(user_id)

        # -------------------------------------------------
        # Load previous conversation
        # -------------------------------------------------

        history = self.memory.get_messages(
            user_id,
            limit=20
        )

        messages = [

            {

                "role":
                    "system",

                "content":
                    SYSTEM_PROMPT

            }

        ]

        # -------------------------------------------------
        # Add memory
        # -------------------------------------------------

        for item in history:

            messages.append({

                "role":
                    item["role"],

                "content":
                    item["content"]

            })

        # -------------------------------------------------
        # Add current message
        # -------------------------------------------------

        messages.append({

            "role":
                "user",

            "content":
                prompt

        })

        errors = []

        # =================================================
        # GEMINI ONLY
        # =================================================

        if AI_PROVIDER == "GEMINI":

            answer = self._gemini(
                messages,
                image
            )

        # =================================================
        # OPENAI ONLY
        # =================================================

        elif AI_PROVIDER == "OPENAI":

            answer = self._openai(
                messages,
                image
            )

        # =================================================
        # AUTO
        # Gemini → OpenAI fallback
        # =================================================

        else:

            answer = None

            if GEMINI_API_KEY:

                try:

                    answer = self._gemini(
                        messages,
                        image
                    )

                except Exception as e:

                    errors.append(
                        f"Gemini: {e}"
                    )

            if not answer and OPENAI_API_KEY:

                try:

                    answer = self._openai(
                        messages,
                        image
                    )

                except Exception as e:

                    errors.append(
                        f"OpenAI: {e}"
                    )

            if not answer:

                raise RuntimeError(
                    "No AI provider was able to respond.\n"
                    + "\n".join(errors)
                )

        # =================================================
        # SAVE MEMORY
        # =================================================

        self.memory.add_message(

            user_id,

            "user",

            prompt

        )

        self.memory.add_message(

            user_id,

            "assistant",

            answer

        )

        return answer
