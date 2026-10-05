"""AI-generated follow-up suggestions for King Zarry AI chat responses.

Suggestions are generated from the actual user message + assistant answer using
the same provider stack as normal text chat. They are not hard-coded categories.
"""
from __future__ import annotations

import json
import re
from typing import Any

import ai_engine


def _parse(raw: str) -> list[str]:
    raw = (raw or "").strip()
    candidates: list[Any] = []
    try:
        value = json.loads(raw)
        if isinstance(value, dict):
            value = value.get("suggestions") or value.get("follow_ups") or value.get("items")
        if isinstance(value, list):
            candidates = value
    except Exception:
        match = re.search(r"\[[\s\S]*\]", raw)
        if match:
            try:
                value = json.loads(match.group(0))
                if isinstance(value, list):
                    candidates = value
            except Exception:
                pass
    out: list[str] = []
    for item in candidates:
        if isinstance(item, str):
            text = re.sub(r"\s+", " ", item).strip().strip('"').strip("'")
            if 3 <= len(text) <= 90 and text.lower() not in {x.lower() for x in out}:
                out.append(text)
        if len(out) >= 3:
            break
    return out[:3]


def generate_suggestions(user_message: str, assistant_response: str) -> list[str]:
    user_message = (user_message or "").strip()[:3000]
    assistant_response = (assistant_response or "").strip()[:6000]
    if not assistant_response:
        return []

    prompt = f"""
Create exactly 3 short, useful follow-up suggestions for the user after the AI response below.

The suggestions MUST be based on the actual conversation and should feel like the natural next things the user might ask, not generic category buttons.
- Do not repeat the user's question.
- Do not suggest actions unrelated to the answer.
- Make each suggestion 2-9 words.
- Make them specific to the answer.
- Return ONLY valid JSON: an array of exactly 3 strings.
- No markdown, no explanation.

USER MESSAGE:
{user_message}

AI RESPONSE:
{assistant_response}
""".strip()

    engine = ai_engine.AIEngine(memory=None)
    methods = [
        ("groq", getattr(engine, "_groq", None), bool(ai_engine.GROQ_API_KEY)),
        ("openrouter", getattr(engine, "_openrouter", None), bool(ai_engine.OPENROUTER_API_KEY)),
        ("chutes", getattr(engine, "_chutes", None), bool(ai_engine.CHUTES_API_KEY)),
        ("gemini", getattr(engine, "_gemini", None), bool(ai_engine.GEMINI_API_KEY)),
    ]

    for name, method, enabled in methods:
        if not enabled or method is None:
            continue
        try:
            raw = method(prompt, [], None, "", False)
            suggestions = _parse(raw or "")
            if len(suggestions) == 3:
                return suggestions
        except Exception:
            continue

    return []
