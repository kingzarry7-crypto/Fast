import base64
import re
import requests
import config

# Fallback config extraction with updated model defaults
GEMINI_API_KEY = getattr(config, "GEMINI_API_KEY", None)
OPENAI_API_KEY = getattr(config, "OPENAI_API_KEY", None)
XAI_API_KEY = getattr(config, "XAI_API_KEY", None)
GROQ_API_KEY = getattr(config, "GROQ_API_KEY", None)

AI_PROVIDER = getattr(config, "AI_PROVIDER", "AUTO").upper().strip()

# Override deprecated gemini-1.5-flash with gemini-2.5-flash
RAW_GEMINI_MODEL = getattr(config, "GEMINI_MODEL", "gemini-2.5-flash")
GEMINI_MODEL = "gemini-2.5-flash" if "1.5" in RAW_GEMINI_MODEL else RAW_GEMINI_MODEL

OPENAI_MODEL = getattr(config, "OPENAI_MODEL", "gpt-4o-mini")
XAI_MODEL = getattr(config, "XAI_MODEL", "grok-beta")
GROQ_MODEL = getattr(config, "GROQ_MODEL", "llama-3.3-70b-versatile")

GEMINI_URL = getattr(config, "GEMINI_URL", "https://generativelanguage.googleapis.com/v1beta/models")
OPENAI_URL = getattr(config, "OPENAI_URL", "https://api.openai.com/v1/chat/completions")
XAI_URL = getattr(config, "XAI_URL", "https://api.x.ai/v1/chat/completions")
GROQ_URL = getattr(config, "GROQ_URL", "https://api.groq.com/openai/v1/chat/completions")

# =========================================================
# KING ZARRY AI 👑
# AI ENGINE
# =========================================================

SYSTEM_PROMPT = """
You are King Zarry AI 👑, the official AI assistant for the King Zarry community.

RESPONSE STYLE:
Be natural, direct, calm and conversational.

DO NOT:
- Say "King Zarry AI here!"
- Say "I can definitely help"
- Give unnecessary introductions
- Ask unnecessary follow-up questions
- Repeat the user's question
- Explain what you are about to do
- Add unnecessary conclusions
- Write long responses to simple questions
- Use excessive headings
- Use excessive emojis
- Add filler
- Ask for information that is not genuinely necessary

When the user asks a simple question:
Answer directly and briefly.

When the user asks for a message:
Give the finished message immediately.

When the user asks for code:
Give the complete code needed.

TRADING:
Be practical and concise.
When live market data is supplied, use it.
When discussing a trading setup, include when relevant:
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
Only claim live market information when actual live market or news data has been supplied by a connected provider.

TONE:
Friendly, confident, helpful and natural.

FORMATTING:
Use clean Discord/Telegram Markdown when useful.
Keep responses easy to read on a phone.
Avoid giant blocks of text.
Use emojis naturally.

DEFAULT LENGTH:
Simple question = short answer.
Normal question = concise answer.
Complex question = detailed only when necessary.

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
        unwanted_openings = [
            r"^king zarry ai here[!,.:\s]*",
            r"^king zarry ai is here[!,.:\s]*",
            r"^sure[!,.:\s]*",
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
        contents = []
        for message in messages:
            role = message.get("role")
            if role == "system":
                continue
            content = message.get(
                "content",
                ""
            )
            if not content:
                continue
            gemini_role = (
                "model"
                if role == "assistant"
                else "user"
            )
            contents.append({
                "role":
                    gemini_role,
                "parts": [
                    {
                        "text":
                            str(content)
                    }
                ]
            })

        # Add image to the latest user message
        if image and contents:
            mime_type, image_bytes = image
            encoded = base64.b64encode(
                image_bytes
            ).decode("utf-8")
            last_parts = contents[-1]["parts"]
            last_parts.append({
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
            "contents":
                contents,
            "generationConfig": {
                "temperature":
                    0.3,
                "maxOutputTokens":
                    700
            }
        }

        base_url = GEMINI_URL.rstrip('/')
        url = f"{base_url}/{GEMINI_MODEL}:generateContent"

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
    # GROQ
    # =====================================================
    def _groq(
        self,
        messages,
        image=None
    ):
        if not GROQ_API_KEY:
            raise RuntimeError(
                "GROQ_API_KEY is not configured."
            )
        prepared = []
        for message in messages:
            prepared.append({
                "role":
                    message["role"],
                "content":
                    message["content"]
            })
        payload = {
            "model":
                GROQ_MODEL,
            "messages":
                prepared,
            "temperature":
                0.3,
            "max_tokens":
                700
        }
        response = requests.post(
            GROQ_URL,
            headers={
                "Authorization":
                    f"Bearer {GROQ_API_KEY}",
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
                f"Groq API error: {error}"
            )
        data = response.json()
        choices = data.get(
            "choices",
            []
        )
        if not choices:
            raise RuntimeError(
                "Groq returned no choices."
            )
        answer = (
            choices[0]
            .get("message", {})
            .get("content", "")
        )
        if not answer:
            raise RuntimeError(
                "Groq returned no text."
            )
        return self._clean_response(
            answer
        )

    # =====================================================
    # GROK / XAI
    # =====================================================
    def _xai(
        self,
        messages,
        image=None
    ):
        if not XAI_API_KEY:
            raise RuntimeError(
                "XAI_API_KEY is not configured."
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
                                data_url
                        }
                    }
                ]
            })
        payload = {
            "model":
                XAI_MODEL,
            "messages":
                prepared,
            "temperature":
                0.3,
            "max_tokens":
                700
        }
        response = requests.post(
            XAI_URL,
            headers={
                "Authorization":
                    f"Bearer {XAI_API_KEY}",
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
                f"xAI API error: {error}"
            )
        data = response.json()
        choices = data.get(
            "choices",
            []
        )
        if not choices:
            raise RuntimeError(
                "xAI returned no choices."
            )
        answer = (
            choices[0]
            .get("message", {})
            .get("content", "")
        )
        if not answer:
            raise RuntimeError(
                "xAI returned no text."
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
            if not content:
                continue
            if role not in (
                "user",
                "assistant"
            ):
                role = "user"
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
        answer = None

        # =================================================
        # SPECIFIC PROVIDER SELECTION
        # =================================================
        if AI_PROVIDER == "GROQ":
            answer = self._groq(
                messages,
                image
            )
        elif AI_PROVIDER == "GEMINI":
            answer = self._gemini(
                messages,
                image
            )
        elif AI_PROVIDER in (
            "GROK",
            "XAI"
        ):
            answer = self._xai(
                messages,
                image
            )
        elif AI_PROVIDER == "OPENAI":
            answer = self._openai(
                messages,
                image
            )
        # =================================================
        # AUTO (Groq → Gemini → Grok → OpenAI)
        # =================================================
        else:
            # -------------------------------------------------
            # GROQ
            # -------------------------------------------------
            if GROQ_API_KEY:
                try:
                    answer = self._groq(
                        messages,
                        image
                    )
                except Exception as e:
                    errors.append(
                        f"Groq: {e}"
                    )

            # -------------------------------------------------
            # GEMINI
            # -------------------------------------------------
            if not answer and GEMINI_API_KEY:
                try:
                    answer = self._gemini(
                        messages,
                        image
                    )
                except Exception as e:
                    errors.append(
                        f"Gemini: {e}"
                    )

            # -------------------------------------------------
            # GROK
            # -------------------------------------------------
            if not answer and XAI_API_KEY:
                try:
                    answer = self._xai(
                        messages,
                        image
                    )
                except Exception as e:
                    errors.append(
                        f"Grok: {e}"
                    )

            # -------------------------------------------------
            # OPENAI
            # -------------------------------------------------
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

            # -------------------------------------------------
            # EVERYTHING FAILED
            # -------------------------------------------------
            if not answer:
                details = " | ".join(errors) if errors else "No API keys configured or valid."
                raise RuntimeError(
                    f"No AI provider was able to respond. ({details})"
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
