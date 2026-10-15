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

try:
    import web_research_engine
except Exception:
    web_research_engine = None


def _env(name: str) -> str:
    return re.sub(r"[\u200b\u200c\u200d\u2060\ufeff]", "", str(os.getenv(name) or "")).strip()


# provider -> (display name, env keys, capabilities, adapter status, integration hint)
KNOWN_PROVIDERS = {
    "shopify": ("Shopify", ["SHOPIFY_CLIENT_ID", "SHOPIFY_CLIENT_SECRET"], ["store_products", "store_orders", "inventory", "store_management"], "native", "Official Shopify Admin API connector with scoped OAuth; write actions must remain approval-gated."),
    "autods": ("AutoDS", ["AUTODS_API_KEY", "AUTODS_MCP_URL"], ["product_research", "product_import", "price_monitoring", "inventory_monitoring", "fulfillment"], "browser_or_mcp", "Use the authenticated AutoDS browser session or an explicitly configured official connector; do not guess an API endpoint."),
    "fiverr": ("Fiverr", ["FIVERR_API_KEY"], ["opportunity_monitoring", "messages", "offers", "delivery"], "browser", "Use the existing isolated Browser Operator for Fiverr. Consequential messages/offers/deliveries require approval."),

    "groq": ("Groq", ["GROQ_API_KEY"], ["text_ai", "vision_ai"], "native", "Already wired into AIEngine."),
    "openrouter": ("OpenRouter", ["OPENROUTER_API_KEY"], ["text_ai", "model_routing"], "native", "Already wired into AIEngine."),
    "chutes": ("Chutes", ["CHUTES_API_KEY"], ["text_ai", "model_routing"], "native", "OpenAI-compatible text fallback is wired into AIEngine; model is controlled by CHUTES_MODEL."),
    "gemini": ("Google Gemini", ["GEMINI_API_KEY"], ["text_ai", "vision_ai"], "native", "Already wired into AIEngine."),
    "xai": ("xAI", ["XAI_API_KEY"], ["text_ai"], "adapter_pending", "Needs a native xAI adapter/provider mapping before direct use."),
    "openai": ("OpenAI", ["OPENAI_API_KEY"], ["text_ai", "vision_ai"], "native", "Direct OpenAI Chat Completions adapter is wired into AIEngine and the streaming chat provider chain; provider selection and model availability still depend on valid Railway environment settings."),
    "cloudflare": ("Cloudflare Workers AI", ["CLOUDFLARE_AI_TOKEN"], ["text_ai", "model_routing"], "native", "OpenAI-compatible provider mapping exists in llm_client.py; verify the Worker URL, token, and selected model with a live request."),
    "huggingface": ("Hugging Face Inference", ["HF_TOKEN", "HUGGINGFACE_API_KEY"], ["text_ai", "model_routing"], "native", "OpenAI-compatible inference-router mapping exists in llm_client.py; configured model availability must be tested."),
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
        ["TRADING_ECONOMICS_API_KEY", "TRADING_ECONOMICS_KEY"],
        ["calendar"],
        "native",
        "Economic-calendar requests are implemented in news.py. Market indicators, financials, forecasts, and news are not yet advertised as wired capabilities.",
    ),
    "massive": (
        "Massive/Polygon",
        ["MASSIVE_API_KEY", "POLYGON_API_KEY"],
        ["market_data"],
        "native",
        "OHLCV aggregate adapter is implemented in market.py with runtime credential lookup and fallback routing; a live authenticated request is still required to verify the account/feed.",
    ),
    "alpaca": ("Alpaca", ["ALPACA_API_KEY", "ALPACA_SECRET_KEY"], ["market_data"], "native", "market.py includes Alpaca market-data requests; both credentials are required and the live data path should be health-tested."),
    "fal": (
        "FAL AI",
        ["FAL_KEY", "FAL_API_KEY"],
        ["video_generation"],
        "partial",
        "A Fal.ai video-generation path exists in discord_bot.py; image/audio generation and app-wide routing are not confirmed wired.",
    ),
    "agnes": ("Agnes AI", ["AGNES_API_KEY"], ["image_generation", "video_generation", "media_editing"], "native", "Media capability is already represented in the app."),
    "acedata": ("AceData Cloud", ["ACEDATA_API_KEY"], ["image_generation", "video_generation"], "native", "Media capability is already represented in the app."),
    "resend": (
        "Resend",
        ["RESEND_API_KEY"],
        ["email_sending", "email_events", "contacts", "broadcasts", "domains", "webhooks", "inbound_email"],
        "native",
        "Resend is already called by api.py for account/workflow email and admin_email_broadcast.py for admin broadcasts; test real delivery and sender-domain configuration.",
    ),
}

# Credentials used by the platform/container itself. They are not "missing API adapters".
KNOWN_SERVICE_CREDENTIALS = {
    "DISCORD_BOT_TOKEN": ("Discord Bot credential", "Platform/service credential; not an external API provider."),
    "TELEGRAM_BOT_TOKEN": ("Telegram Bot credential", "Platform/service credential; not an external API provider."),
    "GPG_KEY": ("Container/system key", "System/container credential; not an application API provider."),
    "KING_ZARRY_SLACK_BRIDGE_KEY": ("Slack bridge secret", "Internal application-to-Slack bridge credential, not a third-party API provider by itself."),
    "KZ_CONNECTOR_ENCRYPTION_KEY": ("Connector encryption key", "Internal application key for protecting connector credentials; not a third-party API provider."),
    "KZ_SANDBOX_RUNNER_TOKEN": ("Sandbox runner token", "Internal application credential for the sandbox runner; not a third-party API provider."),
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
        configured_keys = [e for e in envs if _env(e)]
        if pid == "alpaca":
            configured_by = configured_keys[0] if len(configured_keys) == len(envs) else None
        else:
            configured_by = configured_keys[0] if configured_keys else None
        if not configured_by:
            continue
        providers.append({
            "id": pid,
            "name": name,
            "configured": True,
            "env": configured_by,
            "adapter": adapter,
            "skills": list(skills),
            "needs_code": adapter not in ("native", "partial"),
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

    web_research = {
        "configured": False,
        "instances": 0,
        "searxng_configured": False,
        "tavily_fallback": bool(_env("TAVILY_API_KEY")),
    }
    if web_research_engine is not None:
        try:
            searxng_configured = bool(web_research_engine.is_configured())
            web_research = {
                "configured": searxng_configured or bool(_env("TAVILY_API_KEY")),
                "instances": len(web_research_engine._env_urls()),
                "searxng_configured": searxng_configured,
                "tavily_fallback": bool(_env("TAVILY_API_KEY")),
            }
        except Exception:
            web_research = {
                "configured": bool(_env("TAVILY_API_KEY")),
                "instances": 0,
                "searxng_configured": False,
                "tavily_fallback": bool(_env("TAVILY_API_KEY")),
            }

    return {
        "providers": providers,
        "service_credentials": service_credentials,
        "unknown_env_keys": unknown,
        "configured_count": len(providers),
        "web_research": web_research,
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
    wr = s.get("web_research") or {}
    parts.append(f'web_research:{bool(wr.get("configured"))}|instances={wr.get("instances", 0)}')
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
            if p.get("adapter") == "partial":
                lines.append(f'🟠 <b>{p["name"]}</b> — partially wired; not all listed capabilities are available')
                lines.append(f'   What it can do: <b>{p.get("what_it_can_do", skills)}</b>')
                lines.append(f'   App status: partial integration; live request still needs verification')
                lines.append(f'   Details: {p.get("integration_hint", "Some provider paths exist; verify remaining capabilities.")}')
            elif p["needs_code"]:
                lines.append(f'🟠 <b>{p["name"]}</b> — detected, adapter/code needed')
                lines.append(f'   What it can do: <b>{p.get("what_it_can_do", skills)}</b>')
                lines.append(f'   App status: not wired for direct use yet')
                if p.get("missing"):
                    lines.append(f'   Missing: {", ".join(p["missing"])}')
                lines.append(f'   How to add: {p.get("integration_hint", "Add a provider adapter.")}')
            else:
                lines.append(f'🟢 <b>{p["name"]}</b> — configured + app integration exists')
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

    web_research = s.get("web_research") or {}
    lines.append("")
    if web_research.get("searxng_configured"):
        lines.append(
            f'🌐 <b>Deep Web Research: ACTIVE</b> — '
            f'{web_research.get("instances", 1)} SearXNG instance(s)'
        )
        if web_research.get("tavily_fallback"):
            lines.append("   SearXNG multi-source search + Tavily fallback + public page fetching enabled.")
        else:
            lines.append("   SearXNG multi-source search + public page fetching enabled.")
    elif web_research.get("tavily_fallback"):
        lines.append("🌐 <b>Web Research: ACTIVE (Tavily fallback)</b>")
        lines.append("   Tavily search is configured; SearXNG is optional and adds self-hosted multi-source search.")
    else:
        lines.append("🌐 <b>Deep Web Research: NOT CONFIGURED</b>")
        lines.append("   Add TAVILY_API_KEY for managed web search, or SEARXNG_URL / SEARXNG_URLS for self-hosted multi-source research.")

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
