"""Professional email draft choices for King Zarry AI."""
from __future__ import annotations

import json
import re
import uuid
from typing import Any, Dict


def _ensure_table() -> None:
    from database import get_db_cursor
    with get_db_cursor(commit=True) as cur:
        cur.execute("""
        CREATE TABLE IF NOT EXISTS kz_email_draft_sessions (
          id UUID PRIMARY KEY,
          user_id TEXT NOT NULL,
          recipient TEXT NOT NULL,
          options_json JSONB NOT NULL DEFAULT '[]'::jsonb,
          status TEXT NOT NULL DEFAULT 'pending_choice',
          created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
          updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
        )
        """)
        cur.execute("""
        CREATE INDEX IF NOT EXISTS idx_kz_email_drafts_pending
          ON kz_email_draft_sessions(user_id, status, created_at DESC)
        """)


def _generate_options(recipient: str, subject: str, body: str) -> list[dict[str, str]]:
    """Generate complete draft choices; never silently send the user's brief as the finished email."""
    expected = {"1": "Professional", "2": "Warm and friendly", "3": "Short and direct"}
    prompt = {
        "recipient": recipient,
        "requested_subject": subject,
        "rough_message_or_intent": body,
    }
    parsed = None
    try:
        from llm_client import ask
        response = ask([
            {"role": "system", "content": (
                "You are a careful professional email editor. Rewrite the user's intended message "
                "without inventing facts, promises, attachments, dates, prices, or commitments. "
                "Preserve the meaning. Return ONLY valid JSON array with exactly three objects: id, tone, subject, body. "
                "id 1 must be Professional; id 2 must be Warm and friendly; id 3 must be Short and direct. Do not send."
            )},
            {"role": "user", "content": json.dumps(prompt, ensure_ascii=False)},
        ], max_tokens=1800)
        raw = str(response or "").strip()
        fence = chr(96) * 3
        if raw.startswith(fence):
            raw = raw[len(fence):].strip()
            if raw.lower().startswith("json"):
                raw = raw[4:].strip()
            if raw.endswith(fence):
                raw = raw[:-len(fence)].strip()
        # Be tolerant of leading/trailing commentary around a JSON array.
        left, right = raw.find("["), raw.rfind("]")
        if left >= 0 and right > left:
            raw = raw[left:right + 1]
        candidate = json.loads(raw)
        if isinstance(candidate, list) and len(candidate) == 3:
            parsed = candidate
    except Exception as exc:
        # Invalid model JSON or a provider outage must not block composing an email.
        import logging
        logging.getLogger("kz_email_draft_manager").warning(
            "Email option model unavailable; using safe deterministic drafts (%s)", type(exc).__name__
        )

    options = []
    if parsed is not None:
        try:
            for item in parsed:
                if not isinstance(item, dict):
                    raise ValueError("invalid option shape")
                key = str(item.get("id") or "")
                if key not in expected:
                    continue
                option_subject = " ".join(str(item.get("subject") or subject or "").split())[:300]
                option_body = str(item.get("body") or "").strip()
                if not option_subject or not option_body:
                    raise ValueError("incomplete option")
                # Reject likely truncation instead of letting a partial generated
                # draft proceed to the send-approval step.
                if re.search(r"(?:\\b(?:and|or|with|for|to|because|including|such as|the|a|an)|[,;:—-])\\s*$", option_body, re.I):
                    raise ValueError("email draft appears truncated")
                source_body = str(body or "").strip()
                if len(source_body) >= 500 and len(option_body) < min(int(len(source_body) * 0.65), len(source_body) - 100):
                    raise ValueError("email draft omitted too much of the supplied content")
                options.append({"id": key, "tone": expected[key], "subject": option_subject, "body": option_body[:20000]})
            options.sort(key=lambda x: x["id"])
            if len(options) == 3 and {x["id"] for x in options} == {"1", "2", "3"}:
                return options
            raise ValueError("incomplete email draft options")
        except Exception as exc:
            # Fail closed. Sending the raw prompt/brief as if it were a complete
            # email is the exact failure this guard is designed to prevent.
            raise ValueError("KZ could not generate three complete email drafts. Nothing was sent. Please retry or provide the full email text.") from exc

    raise ValueError("KZ could not generate complete email drafts. Nothing was sent. Please retry or provide the full email text.")


def create_choices(user_id: str, recipient: str, subject: str, body: str) -> Dict[str, Any]:
    recipient, subject, body = str(recipient or "").strip(), str(subject or "").strip(), str(body or "").strip()
    if not recipient or not body:
        raise ValueError("Recipient and message intent are required")
    options = _generate_options(recipient, subject, body)
    _ensure_table()
    from database import get_db_cursor
    session_id = str(uuid.uuid4())
    with get_db_cursor(commit=True) as cur:
        cur.execute(
            "UPDATE kz_email_draft_sessions SET status='superseded',updated_at=NOW() WHERE user_id=%s AND status='pending_choice'",
            (str(user_id),),
        )
        cur.execute("""
          INSERT INTO kz_email_draft_sessions(id,user_id,recipient,options_json,status)
          VALUES (%s,%s,%s,%s::jsonb,'pending_choice')
        """, (session_id, str(user_id), recipient, json.dumps(options, ensure_ascii=False)))
    return {"id": session_id, "recipient": recipient, "options": options}


def _choice_number(text: str) -> str | None:
    value = str(text or "").strip().lower()
    aliases = {
        "1": "1", "option 1": "1", "professional": "1", "choose professional": "1",
        "2": "2", "option 2": "2", "friendly": "2", "warm": "2", "warm and friendly": "2",
        "3": "3", "option 3": "3", "concise": "3", "short": "3", "short and direct": "3",
    }
    return aliases.get(value)


def choose_pending(user_id: str, text: str) -> Dict[str, Any] | None:
    choice = _choice_number(text)
    if not choice:
        return None
    _ensure_table()
    from database import get_db_cursor
    with get_db_cursor(commit=True) as cur:
        cur.execute("""
          SELECT id,recipient,options_json FROM kz_email_draft_sessions
           WHERE user_id=%s AND status='pending_choice'
           ORDER BY created_at DESC LIMIT 1
        """, (str(user_id),))
        row = cur.fetchone()
        if not row:
            return None
        session_id, recipient, raw_options = row[0], str(row[1]), row[2]
        if isinstance(raw_options, str):
            raw_options = json.loads(raw_options)
        options = raw_options if isinstance(raw_options, list) else []
        selected = next((x for x in options if str(x.get("id")) == choice), None)
        if not selected:
            return None
        cur.execute("""
          UPDATE kz_email_draft_sessions SET status='selected',updated_at=NOW()
           WHERE id=%s AND user_id=%s AND status='pending_choice'
        """, (str(session_id), str(user_id)))
    return {
        "session_id": str(session_id),
        "payload": {"to": recipient, "subject": str(selected["subject"]), "body": str(selected["body"])},
        "tone": str(selected["tone"]),
    }


def render_choices(session: Dict[str, Any]) -> str:
    lines = ["✉️ EMAIL DRAFT OPTIONS", "", f"To: {session['recipient']}",
             "Choose 1, 2, or 3. Nothing has been sent.", ""]
    for option in session["options"]:
        lines.extend([f"{option['id']}. {option['tone']}",
                      f"Subject: {option['subject']}", option["body"], ""])
    lines.append("After you choose, KZ will show the final exact email and ask you to approve sending.")
    return "\n".join(lines)
