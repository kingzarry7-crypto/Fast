"""api.py bootstrap: load known-good source + patches. Cache bust v5."""
import os
import urllib.request

GOOD_URL = "https://raw.githubusercontent.com/kingzarry7-crypto/Fast/d53e44a4f5f511f7660bd02f3db0852a8cb36462/api.py"
CACHE_NAME = "_api_good_cache_v5.py"


def _parse_admin_emails():
    raw = ",".join(
        [os.getenv("ADMIN_EMAILS") or "", os.getenv("ADMIN_EMAIL") or ""]
    )
    out = set()
    for part in raw.split(","):
        p = part.strip().strip('"').strip("'").lower()
        if p and "@" in p:
            out.add(p)
    return out


def _load_good():
    path = os.path.join(os.path.dirname(__file__), CACHE_NAME)
    if not os.path.isfile(path) or os.path.getsize(path) < 10000:
        with urllib.request.urlopen(GOOD_URL, timeout=60) as resp:
            data = resp.read()
        with open(path, "wb") as f:
            f.write(data)
    with open(path, "r", encoding="utf-8") as f:
        code = f.read()
    ns = {"__name__": "api", "__file__": path}
    exec(compile(code, path, "exec"), ns, ns)

    # CRITICAL: good api.py references these but never assigns them → NameError on admin
    ns["ADMIN_EMAILS"] = _parse_admin_emails()
    ns["ADMIN_PASSWORD"] = (os.getenv("ADMIN_PASSWORD") or "").strip()
    ns["ADMIN_SESSION_COOKIE"] = (
        os.getenv("ADMIN_SESSION_COOKIE") or "king_zarry_admin_session"
    ).strip()
    try:
        ns["ADMIN_SESSION_DAYS"] = max(
            1, min(int(os.getenv("ADMIN_SESSION_DAYS", "7") or 7), 90)
        )
    except Exception:
        ns["ADMIN_SESSION_DAYS"] = 7

    print(
        "ADMIN_ENV",
        "emails=",
        len(ns["ADMIN_EMAILS"]),
        "password_set=",
        bool(ns["ADMIN_PASSWORD"]),
        flush=True,
    )

    try:
        from admin_stats_fix import install_admin_stats_fix

        install_admin_stats_fix(
            ns["app"],
            require_admin=ns["_require_admin"],
            get_db_cursor=ns["get_db_cursor"],
            row_value=ns["_row_value"],
            ensure_billing_tables=ns.get("_ensure_billing_tables"),
            is_database_configured=ns.get("is_database_configured"),
            require_current_user=ns.get("_require_current_user"),
            is_admin_email=ns.get("_is_admin_email"),
            has_valid_admin_session=ns.get("_has_valid_admin_session"),
            admin_password=ns.get("ADMIN_PASSWORD") or "",
            admin_emails=ns.get("ADMIN_EMAILS"),
        )
        print("ADMIN_PATCHES_INSTALLED", flush=True)
    except Exception as e:
        print("ADMIN_PATCHES_FAILED", type(e).__name__, str(e)[:120], flush=True)

    try:
        from admin_email_broadcast import install_email_broadcast

        install_email_broadcast(
            ns["app"],
            require_admin=ns["_require_admin"],
            get_db_cursor=ns["get_db_cursor"],
            row_value=ns["_row_value"],
            send_email_resend=ns["_send_email_resend"],
            resend_api_key=ns["RESEND_API_KEY"],
            email_from=ns["EMAIL_FROM"],
        )
    except Exception as e:
        print("EMAIL_BROADCAST_INSTALL_FAILED", type(e).__name__, flush=True)

    g = globals()
    for k, v in ns.items():
        if not k.startswith("__"):
            g[k] = v


_load_good()


# Slack integration is additive and does not replace the existing API.
try:
    from slack_integration import install_slack_integration
    install_slack_integration(globals().get("app"))
except Exception as e:
    print("SLACK_INTEGRATION_INSTALL_FAILED", type(e).__name__, str(e)[:160], flush=True)

# Optional WebRTC realtime voice is additive. Existing voice/chat remains the fallback.
try:
    from realtime_voice import install_realtime_voice

    def _save_realtime_transcript(user_id, conversation_id, role, content):
        adapter = WebMemoryAdapter(user_id, conversation_id=conversation_id)
        adapter.add_message(user_id, role, content)
        return {"conversation_id": adapter.conversation_id, "message_id": None}

    install_realtime_voice(
        globals().get("app"),
        require_current_user=globals().get("_require_current_user"),
        save_transcript=_save_realtime_transcript,
    )
    print("REALTIME_VOICE_PATCH_INSTALLED", flush=True)
except Exception as e:
    print("REALTIME_VOICE_PATCH_FAILED", type(e).__name__, str(e)[:160], flush=True)


# Optional additive SSE text streaming. Existing /api/chat remains unchanged.
try:
    from streaming_chat import install_streaming_chat

    install_streaming_chat(
        globals().get("app"),
        require_current_user=globals().get("_require_current_user"),
        get_or_create_conversation=globals().get("_get_or_create_conversation"),
        maybe_set_conversation_title=globals().get("_maybe_set_conversation_title"),
        memory_factory=lambda user_id, conversation_id: WebMemoryAdapter(
            user_id, conversation_id=conversation_id
        ),
    )
except Exception as e:
    print("TEXT_STREAMING_PATCH_FAILED", type(e).__name__, str(e)[:160], flush=True)

# Optional V5.2 unified cross-platform memory. Additive: existing memory remains fallback.
try:
    from unified_memory_patch import install_web_memory_bridge

    install_web_memory_bridge(
        globals().get("app"),
        WebMemoryAdapter,
        globals().get("_require_current_user"),
    )
except Exception as e:
    print("UNIFIED_MEMORY_BRIDGE_PATCH_FAILED", type(e).__name__, str(e)[:160], flush=True)
