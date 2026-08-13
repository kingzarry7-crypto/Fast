import base64
import re
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
You are King Zarry AI 👑, the official AI assistant for the King Zarry community.

IMPORTANT RESPONSE STYLE:

Be natural, direct, calm and conversational.

DO NOT:
- Say "King Zarry AI here!"
- Say "I can definitely help"
- Give unnecessary introductions
- Ask unnecessary follow-up questions
- Give numbered lists unless the user asks for a list
- Give multiple example answers unless requested
- Repeat the user's question
- Explain what you are about to do
- Add unnecessary conclusions
- Write long responses to simple questions
- Use excessive headings
- Use excessive emojis
- Add filler such as "In the meantime"
- Tell the user to provide more information when you can reasonably answer with what they already gave you

WHEN THE USER ASKS A SIMPLE QUESTION:
Answer directly in 1-5 short paragraphs or concise bullets.

WHEN THE USER ASKS FOR A MESSAGE:
Give the finished message immediately.
Do not ask who the person is or what the goal is unless that information is genuinely required.

WHEN THE USER ASKS FOR CODE:
Give the complete code needed and clearly state where it goes.

WHEN THE USER ASKS ABOUT TRADING:
Be practical and concise.
Include relevant:
• Direction
• Entry
• Stop loss / invalidation
• Take profit
• Risk/reward
• Reason

Never guarantee profit.

Never claim certainty about future market movement.

Clearly distinguish:
CONFIRMED
PROBABLE
UNCERTAIN

Never pretend to have live market data.
Only claim live market information when actual live market data has been supplied by a connected market/news provider.

TRADING SAFETY:
Trading carries risk. Do not promise guaranteed profits or tell the user a trade is certain to win.

CONVERSATION:
Remember useful context from the conversation and avoid making the user repeat information unnecessarily.

TONE:
Friendly, confident, helpful and natural.
Sound like a real assistant, not a customer-support script.

FORMATTING:
Use clean Discord/Telegram Markdown when useful.
Keep messages easy to read on a phone.
Avoid giant blocks of text.
Use emojis naturally, not excessively.

DEFAULT RESPONSE LENGTH:
Simple question = short answer.
Normal question = concise answer.
Complex question = detailed answer only when necessary.

You are King Zarry AI 👑.
"""


class AIEngine:

    def __init__(self, memory):
        self.memory = memory

    # =====================================================
    # CLEAN RESPONSE
    # =====================================================

    def _clean_response(self, text):

        if not text:
            return text

        text = str(text).strip()

        # Remove common unnecessary AI introductions
        unwanted_openings = [
            r"^king zarry ai here[!,.:\s]*",
            r"^king zarry ai is here[!,.:\s]*",
            r"^sure[!,.:\s]*i can definitely help[.!:\s]*",
            r"^absolutely[!,.:\s]*",
            r"^of course[!,.:\s]*",
            r"^i can definitely help[!,.:\s]*",
            r"^i'd be happy to help[!,.:\s]*",
        ]

        for pattern in unwanted_openings:
            text = re.sub(
                pattern,
                "",
                text,
                flags=re.IGNORECASE
            )

        # Remove excessive blank lines
        text = re.sub(
            r"\n{3,}",
            "\n\n",
            text
        )

        # Remove excessive spaces
        text = re.sub(
            r"[ \t]{3,}",
            " ",
            text
        )

        return text.strip()

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

        # Give Gemini the conversation context
        for message in messages:

            role = message.get("role")

            if role == "system":
                continue

            content = message.get(
                "content",
                ""
            )

            if content:
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

                    "mime_type":
                        mime_type,

                    "data":
                        encoded

                }

            })

        payload = {

            "systemInstruction": {

                "parts": [

                    {
                        "text":
                            SYSTEM_PROMPT
                    }

                ]

            },

            "contents": [

                {

                    "role":
                        "user",

                    "parts":
                        parts

                }

            ],

            "generationConfig": {

                "temperature":
                    0.3,

                "maxOutputTokens":
                    700

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

        return self._clean_response(
            answer
        )

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

                "role":
                    "user",

                "content": [

                    {

                        "type":
                            "text",

                        "text":
                            "Analyze the attached image carefully and answer directly."

                    },

                    {

                        "type":
                            "image_url",

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
                700

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

        return self._clean_response(
            answer
        )

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

        history = self.memory.get_messages(
            user_id,
            limit=12
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
        # MEMORY
        # -------------------------------------------------

        for item in history:

            role = item.get(
                "role",
                "user"
            )

            content = item.get(
                "content",
                ""
            )

            if content:

                messages.append({

                    "role":
                        role,

                    "content":
                        content

                })

        # -------------------------------------------------
        # CURRENT MESSAGE
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
        # GEMINI → OPENAI
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
        # FINAL CLEANUP
        # =================================================

        answer = self._clean_response(
            answer
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
