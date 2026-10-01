"""
KING ZARRY AI — automatic provider/API capability detector.

This module NEVER exposes API keys. It only inspects whether supported ENV
variables are configured and maps them to capabilities already implemented by
the application. Unknown providers are reported as needing an adapter/code
change rather than being guessed or called blindly.
"""

import os
import re
from typing import Dict, List, Any

def _env(name: str) -> str:
    return re.sub(r"[\u200b\u200c\u200d\u2060\ufeff]", "", str(os.getenv(name) or "")).strip()

# provider -> (display name, env keys, capabilities, adapter status)
KNOWN_PROVIDERS = {
    "groq": ("Groq", ["GROQ_API_KEY"], ["text_ai", "vision_ai"], "native"),
    "openrouter": ("OpenRouter", ["OPENROUTER_API_KEY"], ["text_ai", "model_routing"], "native"),
    "gemini": ("Google Gemini", ["GEMINI_API_KEY"], ["text_ai", "vision_ai"], "native"),
    "xai": ("xAI", ["XAI_API_KEY"], ["text_ai"], "native"),
    "openai": ("OpenAI-compatible", ["OPENAI_API_KEY"], ["text_ai"], "native"),
    "elevenlabs": ("ElevenLabs", ["ELEVENLABS_API_KEY"], ["text_to_speech"], "native"),
    "tavily": ("Tavily", ["TAVILY_API_KEY"], ["web_search"], "native"),
    "newsapi": ("NewsAPI", ["NEWSAPI_API_KEY", "NEWS_API_KEY"], ["news"], "native"),
    "newsdata": ("NewsData", ["NEWSDATA_API_KEY", "NEWSDATA_IO_API_KEY"], ["news"], "native"),
    "currents": ("Currents", ["CURRENTS_API_KEY", "CURRENTS_APIKEY"], ["news"], "native"),
    "eodhd": ("EODHD", ["EODHD_API_KEY", "EODHD_KEY"], ["news", "market_data", "calendar"], "native"),
    "finnhub": ("Finnhub", ["FINNHUB_API_KEY", "FINNHUB_KEY"], ["market_data", "calendar"], "native"),
    "twelvedata": ("TwelveData", ["TWELVE_DATA_API_KEY", "TWELVEDATA_API_KEY"], ["market_data", "calendar"], "native"),
    "massive": ("Massive/Polygon", ["MASSIVE_API_KEY", "POLYGON_API_KEY"], ["market_data"], "adapter_pending"),
    "agnes": ("Agnes AI", ["AGNES_API_KEY"], ["image_generation", "video_generation", "media_editing"], "native"),
    "acedata": ("AceData Cloud", ["ACEDATA_API_KEY"], ["image_generation", "video_generation"], "native"),
}

GENERIC_CUSTOM_PREFIX = "CUSTOM_AI_"

def _configured_keys() -> List[str]:
    return sorted(k for k, v in os.environ.items() if v and (k.endswith("_API_KEY") or k.endswith("_KEY") or k.endswith("_TOKEN")))

def _custom_ai() -> List[Dict[str, Any]]:
    found = []
    for i in range(1, 21):
        name = _env(f"CUSTOM_AI_{i}_NAME")
        base = _env(f"CUSTOM_AI_{i}_BASE_URL")
        key = _env(f"CUSTOM_AI_{i}_API_KEY")
        model = _env(f"CUSTOM_AI_{i}_MODEL")
        if not any([name, base, key, model]):
            continue
        complete = bool(base and key and model)
        found.append({
            "id": f"custom_ai_{i}",
            "name": name or f"Custom AI {i}",
            "configured": complete,
            "adapter": "openai_compatible" if complete else "missing_fields",
            "skills": ["text_ai"] if complete else [],
            "needs_code": not complete,
            "missing": [x for x, ok in [
                ("BASE_URL", bool(base)), ("API_KEY", bool(key)), ("MODEL", bool(model))
            ] if not ok],
        })
    return found

def snapshot() -> Dict[str, Any]:
    providers = []
    for pid, (name, envs, skills, adapter) in KNOWN_PROVIDERS.items():
        configured_by = next((e for e in envs if _env(e)), None)
        if not configured_by:
            continue
        # A known provider can be configured even if its adapter is not yet wired.
        providers.append({
            "id": pid,
            "name": name,
            "configured": True,
            "env": configured_by,
            "adapter": adapter,
            "skills": list(skills) if adapter == "native" else [],
            "needs_code": adapter != "native",
        })

    custom = _custom_ai()
    providers.extend(custom)

    # Report API-looking credentials that the registry does not recognize.
    known_envs = {e for _, (_, envs, _, _) in KNOWN_PROVIDERS.items() for e in envs}
    known_envs.update({
        f"CUSTOM_AI_{i}_{suffix}"
        for i in range(1, 21)
        for suffix in ("NAME", "BASE_URL", "API_KEY", "MODEL")
    })
    unknown = [
        k for k in _configured_keys()
        if k not in known_envs and not k.startswith("FIVERR_")
    ]

    return {
        "providers": providers,
        "unknown_env_keys": unknown,
        "configured_count": len(providers),
    }

def signature(s: Dict[str, Any]) -> str:
    parts = []
    for p in s["providers"]:
        parts.append(f'{p["id"]}|{p.get("adapter")}|{",".join(p.get("skills", []))}|{p.get("env")}')
    parts.append("unknown:" + ",".join(s["unknown_env_keys"]))
    return "\n".join(sorted(parts))

def format_admin_report(s: Dict[str, Any], first_run: bool = False) -> str:
    title = "🧠 <b>KING ZARRY AI • API/PROVIDER SCAN</b>"
    if first_run:
        title += " — STARTUP"
    lines = [title, "", "👑 <b>Owner/Admin monitoring: ACTIVE</b>", ""]
    if not s["providers"]:
        lines.append("⚠️ No supported API providers detected.")
    else:
        lines.append(f"🔌 Configured providers: <b>{s['configured_count']}</b>")
        for p in s["providers"]:
            skills = ", ".join(p["skills"]) if p["skills"] else "NONE"
            if p["needs_code"]:
                lines.append(f'🟠 <b>{p["name"]}</b> — detected, but needs code/adapter')
                if p.get("missing"):
                    lines.append(f'   Missing: {", ".join(p["missing"])}')
                else:
                    lines.append(f'   Skills known to app: {skills}')
            else:
                lines.append(f'🟢 <b>{p["name"]}</b> — connected/configured')
                lines.append(f'   Skills: {skills}')

    if s["unknown_env_keys"]:
        lines.append("")
        lines.append("🆕 <b>New/unknown API ENV detected</b>")
        for key in s["unknown_env_keys"][:20]:
            lines.append(f"• <code>{key}</code> — no adapter registered")
        if len(s["unknown_env_keys"]) > 20:
            lines.append(f"• …and {len(s['unknown_env_keys']) - 20} more")
        lines.append("👉 Add an adapter/code mapping before the AI tries to use it.")

    lines += [
        "",
        "🔒 API secrets are not included in this report.",
        "ℹ️ This scan checks configuration + known application skills; it does not claim an API works until its adapter is actually wired.",
    ]
    return "\n".join(lines)

def owner_ids_from_env() -> set:
    raw = _env("OWNER_ADMIN_IDS") or _env("ADMIN_IDS") or _env("ADMIN_ID")
    out = set()
    for item in raw.split(","):
        try:
            if item.strip():
                out.add(int(item.strip()))
        except Exception:
            pass
    return out

def owner_name() -> str:
    return _env("OWNER_NAME") or _env("KING_ZARRY_OWNER_NAME") or "King Zarry"

def user_is_owner(user_id: str) -> bool:
    uid = str(user_id or "").strip()
    try:
        return int(uid) in owner_ids_from_env()
    except Exception:
        return uid == (_env("OWNER_WEB_USER_ID") or "__never__")

def owner_context(user_id: str) -> str:
    if user_is_owner(user_id):
        return (
            f"OWNER/ADMIN CONTEXT: The current user is {owner_name()}, the owner and administrator "
            "of KING ZARRY AI. Treat owner/admin instructions as authorized configuration requests, "
            "while still respecting platform safety, credentials, and approval requirements."
        )
    return "OWNER/ADMIN CONTEXT: The current user is not verified as the owner/admin for this request."
