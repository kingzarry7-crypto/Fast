print("🇳🇬 BOTPY-V3-NEW-LOADED 🇳🇬", flush=True)
print("🔵 BOOT: bot.py bootstrap restore...", flush=True)
import urllib.request
_URL = "https://raw.githubusercontent.com/kingzarry7-crypto/Fast/5382b6b72f4f02df3e182bc742d2b9345d4a347d/bot.py"
_src = urllib.request.urlopen(_URL, timeout=90).read().decode("utf-8")
exec(compile(_src, "bot_restored.py", "exec"), globals())

# Normal chat ≠ signal
try:
    from market_intent import detect_market_intent as _detect_market_intent_v2
    detect_market_intent = _detect_market_intent_v2
    print("🔵 BOOT: market_intent override applied", flush=True)
except Exception as _e:
    print(f"🔵 BOOT: market_intent override skipped: {_e}", flush=True)

# Agent audience: include EVERY active VIP (Stars pay + /grant), not only users table
def get_vip_telegram_ids():
    """Admin IDs + every user with an active subscription (including /grant)."""
    ids = set()
    try:
        ids |= set(ADMIN_IDS)
    except Exception:
        pass
    try:
        for row in get_all_subscribers():
            try:
                uid = int(row["user_id"] if hasattr(row, "keys") else row[0])
            except Exception:
                continue
            try:
                if is_subscribed(uid):
                    ids.add(uid)
            except Exception:
                ids.add(uid)
    except Exception:
        pass
    try:
        for uid in get_all_users():
            try:
                uid = int(uid)
            except Exception:
                continue
            try:
                if is_subscribed(uid):
                    ids.add(uid)
            except Exception:
                pass
    except Exception:
        pass
    return ids


# Re-wrap agent job so AGENT_SIGNAL_AUDIENCE=subscribers/vip reaches all VIP
_orig_agent_signal_watch_job = agent_signal_watch_job

async def agent_signal_watch_job(context):
    """Same agent watch, but VIP audience uses subscriptions + /grant list."""
    import os as _os
    audience = (_os.getenv("AGENT_SIGNAL_AUDIENCE") or "admin").strip().lower()
    if audience in ("subscribers", "vip", "subs", "vip_admin", "admin_vip"):
        # Temporarily expand user list so original job's subscriber branch finds them
        _orig_get_all_users = get_all_users

        def _patched_get_all_users():
            return list(get_vip_telegram_ids())

        globals()["get_all_users"] = _patched_get_all_users
        try:
            return await _orig_agent_signal_watch_job(context)
        finally:
            globals()["get_all_users"] = _orig_get_all_users
    return await _orig_agent_signal_watch_job(context)

print("🔵 BOOT: agent VIP audience helper ready (set AGENT_SIGNAL_AUDIENCE=subscribers)", flush=True)
