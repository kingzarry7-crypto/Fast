""" 
KING ZARRY AI — automatic provider/API capability detector.

This module NEVER exposes API keys. It inspects configured ENV variables and
describes what a detected provider is known to do, what KING ZARRY AI already
has wired, and what adapter/code is still needed.

Unknown credentials are classified conservatively. The scanner does not guess
that an arbitrary secret is an API provider.
"""

import os
import re
from typing import Dict, List, Any

try:
    import universal_api_discovery
except Exception:
    universal_api_discovery = None


def _env(name: str) -> str:
    return re.sub(r"[\u200b\u200c\u200d\u2060\ufeff]", "", str(os.getenv(name) or "")).strip()


# provider -> (display name, env keys, capabilities, adapter status, integration hint)
KNOWN_PROVIDERS = {
    "groq": ("Groq", ["GROQ_API_KEY"], ["text_ai", "vision_ai"], "native", "Already wired into AIEngine."),
    "openrouter": ("OpenRouter", ["OPENROUTER_API_KEY"], ["text_ai", "model_routing"], "native", "Already wired into AIEngine."),
    "gemini": ("Google Gemini", ["GEMINI_API_KEY"], ["text_ai", "vision_ai"], "native", "Already wired into AIEngine."),
    "xai": ("xAI", ["XAI_API_KEY"], ["text_ai"], "adapter_pending", "Needs a native xAI adapter/provider mapping before direct use."),
    "openai": ("OpenAI", ["OPENAI_API_KEY"], ["text_ai", "vision_ai"], "adapter_pending", "Needs a native OpenAI adapter/provider mapping before direct use."),
    "elevenlabs": ("ElevenLabs", ["ELEVENLABS_API_KEY"], ["text_to_speech", "voice"], "native", "Voice/TTS capability is already represented in the app."),
    "tavily": ("Tavily", ["TAVILY_API_KEY"], ["web_search"], "native", "Web-search capability is already represented in the app."),
    "newsapi": ("NewsAPI", ["NEWSAPI_API_KEY", "NEWS_API_KEY"], ["news"], "native", "News provider is already represented in news.py."),
    "newsdata": ("NewsData", ["NEWSDATA_API_KEY", "NEWSDATA_IO_API_KEY"], ["news"], "native", "News provider is already represented in news.py."),
    "currents": ("Currents", ["CURRENTS_API_KEY", "CURRENTS_APIKEY"], ["news"], "native", "News provider is already represented in news.py."),
    "eodhd": ("EODHD", ["EODHD_API_KEY", "EODHD_KEY"], ["news", "market_data", "calendar"], "native", "News/market/calendar provider is already represented in news.py."),
    "finnhub": ("Finnhub", ["FINNHUB_API_KEY", "FINNHUB_KEY"], ["market_data", "calendar"], "native", "Market/calendar capability is already represented in news.py."),
    "twelvedata": ("TwelveData", ["TWELVE_DATA_API_KEY", "TWELVEDATA_API_KEY"], ["market_data", "calendar"], "native", "Market/calendar capability is already represented in news.py."),
    "trading_economics": (
        "Trading Economics",
        ["TRADING_ECONOMICS_API_KEY"],
        ["economic_indicators", "market_data", "calendar", "financials", "forecasts", "news"],
        "adapter_pending",
        "Needs an adapter in news/market/calendar code before the AI can call it directly.",
    ),
    "massive": ("Massive/Polygon", ["MASSIVE_API_KEY", "POLYGON_API_KEY"], ["market_data"], "adapter_pending", "Needs a native market-data adapter before direct use."),
    "fal": (
        "FAL AI",
        ["FAL_KEY", "FAL_API_KEY"],
        ["image_generation", "video_generation", "audio_generation", "media_generation"],
        "adapter_pending",
        "Needs a FAL adapter/model router; FAL_KEY alone does not automatically wire the service.",
    ),
    "agnes": ("Agnes AI", ["AGNES_API_KEY"], ["image_generation", "video_generation", "media_editing"], "native", "Media capability is already represented in the app."),
    "acedata": ("AceData Cloud", ["ACEDATA_API_KEY"], ["image_generation", "video_generation"], "native", "Media capability is already represented in the app."),
    "resend": (
        "Resend",
        ["RESEND_API_KEY"],
        ["email_sending", "email_events", "contacts", "broadcasts", "domains", "webhooks", "inbound_email"],
        "adapter_pending",
        "Needs an email adapter; useful for registration/verification emails and agent email workflows.",
    ),
}

# Credentials used by the platform/container itself. They are not "missing API adapters".
KNOWN_SERVICE_CREDENTIALS = {
    "DISCORD_BOT_TOKEN": ("Discord Bot credential", "Platform/service credential; not an external API provider."),
    "TELEGRAM_BOT_TOKEN": ("Telegram Bot credential", "Platform/service credential; not an external API provider."),
    "GPG_KEY": ("Container/system key", "System/container credential; not an application API provider."),
}

GENERIC_CUSTOM_PREFIX = "CUSTOM_AI_"


def _configured_keys() -> List[str]:
    return sorted(
        k for k, v in os.environ.items()
        if v and (k.endswith("_API_KEY") or k.endswith("_KEY") or k.endswith("_TOKEN"))
    )


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
            "env": f"CUSTOM_AI_{i}_API_KEY" if key else None,
            "adapter": "openai_compatible" if complete else "missing_fields",
            "skills": ["text_ai"] if complete else [],
            "needs_code": not complete,
            "what_it_can_do": "OpenAI-compatible text/model API" if complete else "Custom AI configuration is incomplete.",
            "integration_hint": "Can use the generic OpenAI-compatible adapter." if complete else "Add BASE_URL, API_KEY, and MODEL.",
            "missing": [
                x for x, ok in [
                    ("BASE_URL", bool(base)),
                    ("API_KEY", bool(key)),
                    ("MODEL", bool(model)),
                ] if not ok
            ],
        })
    return found


def snapshot() -> Dict[str, Any]:
    providers = []
    for pid, (name, envs, skills, adapter, hint) in KNOWN_PROVIDERS.items():
        configured_by = next((e for e in envs if _env(e)), None)
        if not configured_by:
            continue
        providers.append({
            "id": pid,
            "name": name,
            "configured": True,
            "env": configured_by,
            "adapter": adapter,
            "skills": list(skills) if adapter == "native" else list(skills),
            "needs_code": adapter != "native",
            "what_it_can_do": ", ".join(skills),
            "integration_hint": hint,
        })

    custom = _custom_ai()
    providers.extend(custom)

    known_envs = {e for _, (_, envs, _, _, _) in KNOWN_PROVIDERS.items() for e in envs}
    known_envs.update(KNOWN_SERVICE_CREDENTIALS.keys())
    known_envs.update({
        f"CUSTOM_AI_{i}_{suffix}"
        for i in range(1, 21)
        for suffix in ("NAME", "BASE_URL", "API_KEY", "MODEL")
    })

    unknown = [
        k for k in _configured_keys()
        if k not in known_envs and not k.startswith("FIVERR_")
    ]

    service_credentials = [
        {
            "env": key,
            "name": name,
            "what_it_is": description,
        }
        for key, (name, description) in KNOWN_SERVICE_CREDENTIALS.items()
        if _env(key)
    ]

    universal = {"providers": [], "configured_count": 0}
    if universal_api_discovery is not None:
        try:
            universal = universal_api_discovery.snapshot()
            providers.extend(universal.get("providers", []))
        except Exception as exc:
            universal = {"providers": [], "configured_count": 0, "error": type(exc).__name__}

    return {
        "providers": providers,
        "service_credentials": service_credentials,
        "unknown_env_keys": unknown,
        "configured_count": len(providers),
        "universal_api_count": len(universal.get("providers", [])),
        "universal_api_tools": (
            universal_api_discovery.tool_catalog()
            if universal_api_discovery is not None else []
        ),
    }


def signature(s: Dict[str, Any]) -> str:
    parts = []
    for p in s["providers"]:
        parts.append(
            f'{p["id"]}|{p.get("adapter")}|{",".join(p.get("skills", []))}|{p.get("env")}'
        )
    parts.append("services:" + ",".join(x["env"] for x in s.get("service_credentials", [])))
    parts.append("unknown:" + ",".join(s["unknown_env_keys"]))
    if universal_api_discovery is not None:
        try:
            parts.append("universal:" + universal_api_discovery.signature({
                "providers": [
                    p for p in s.get("providers", [])
                    if p.get("adapter") in ("openapi_generic", "discovery_pending")
                ]
            }))
        except Exception:
            pass
    return "\n".join(sorted(parts))


def _skill_lines(skills: List[str]) -> str:
    return ", ".join(skills) if skills else "NONE"


def format_admin_report(s: Dict[str, Any], first_run: bool = False) -> str:
    title = "🧠 <b>KING ZARRY AI • API/PROVIDER SCAN</b>"
    if first_run:
        title += " — STARTUP"

    lines = [
        title,
        "",
        "👑 <b>Owner/Admin monitoring: ACTIVE</b>",
        "",
    ]

    if not s["providers"]:
        lines.append("⚠️ No supported API providers detected.")
    else:
        lines.append(f"🔌 Configured providers: <b>{s['configured_count']}</b>")
        for p in s["providers"]:
            skills = _skill_lines(p.get("skills", []))
            if p["needs_code"]:
                lines.append(f'🟠 <b>{p["name"]}</b> — detected, adapter/code needed')
                lines.append(f'   What it can do: <b>{p.get("what_it_can_do", skills)}</b>')
                lines.append(f'   App status: not wired for direct use yet')
                if p.get("missing"):
                    lines.append(f'   Missing: {", ".join(p["missing"])}')
                lines.append(f'   How to add: {p.get("integration_hint", "Add a provider adapter.")}')
            else:
                lines.append(f'🟢 <b>{p["name"]}</b> — configured + app skill exists')
                lines.append(f'   What it can do: <b>{p.get("what_it_can_do", skills)}</b>')
                lines.append(f'   App status: ready through existing integration')
                if p.get("integration_hint"):
                    lines.append(f'   Integration: {p["integration_hint"]}')

    if s.get("service_credentials"):
        lines.append("")
        lines.append("⚪ <b>Platform/system credentials</b>")
        for item in s["service_credentials"]:
            lines.append(f'• <code>{item["env"]}</code> — {item["name"]}')
            lines.append(f'  {item["what_it_is"]}')

    universal_items = [
        p for p in s.get("providers", [])
        if p.get("adapter") in ("openapi_generic", "discovery_pending")
    ]
    if universal_items:
        lines.append("")
        lines.append("🧩 <b>Universal API Learning</b>")
        if universal_api_discovery is not None:
            try:
                lines.extend(universal_api_discovery.report_lines({"providers": universal_items}))
            except Exception:
                pass

    if s["unknown_env_keys"]:
        lines.append("")
        lines.append("🆕 <b>Unrecognized API-like ENV detected</b>")
        for key in s["unknown_env_keys"][:20]:
            lines.append(f"• <code>{key}</code> — provider identity not known yet")
            lines.append("  What it can do: unknown until the provider is identified")
            lines.append("  How to add: tell the owner the provider name/API docs, then add an adapter mapping")
        if len(s["unknown_env_keys"]) > 20:
            lines.append(f"• …and {len(s['unknown_env_keys']) - 20} more")

    lines += [
        "",
        "📌 <b>Legend</b>",
        "🟢 Configured and an existing KING ZARRY AI skill is wired.",
        "🟠 API detected and its capabilities are known, but code/adapter is still needed.",
        "⚪ Platform/system credential — not an API skill to add.",
        "🆕 Unknown API-like credential — identify it before wiring.",
        "",
        "🔒 API secrets are never included in this report.",
        "ℹ️ Configuration does not prove an API works. A provider is only callable after its adapter/skill is wired and health/auth checks pass.",
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
