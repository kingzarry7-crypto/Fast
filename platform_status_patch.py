"""Additive platform connectivity/status endpoints for Settings UI."""
import os
import urllib.request
import json


def _clean(value):
    return str(value or "").strip()


def _telegram_status():
    token = _clean(os.getenv("TELEGRAM_BOT_TOKEN"))
    if not token:
        return {"configured": False, "reachable": False, "username": None, "url": None}
    try:
        req = urllib.request.Request(
            f"https://api.telegram.org/bot{token}/getMe",
            headers={"User-Agent": "King-Zarry-AI/5.0"},
        )
        with urllib.request.urlopen(req, timeout=5) as response:
            payload = json.loads(response.read().decode("utf-8"))
        result = payload.get("result") or {}
        username = _clean(result.get("username"))
        return {
            "configured": True,
            "reachable": bool(payload.get("ok") and username),
            "username": username or None,
            "url": f"https://t.me/{username}" if username else None,
        }
    except Exception as exc:
        return {
            "configured": True,
            "reachable": False,
            "username": None,
            "url": None,
            "error": type(exc).__name__,
        }


def _discord_status():
    token = _clean(os.getenv("DISCORD_BOT_TOKEN"))
    invite = _clean(
        os.getenv("DISCORD_INVITE_URL")
        or os.getenv("NEXT_PUBLIC_DISCORD_INVITE_URL")
    )
    if not token:
        return {
            "configured": False,
            "reachable": False,
            "invite_url": invite or None,
        }
    try:
        req = urllib.request.Request(
            "https://discord.com/api/v10/users/@me",
            headers={
                "Authorization": f"Bot {token}",
                "User-Agent": "King-Zarry-AI/5.0",
            },
        )
        with urllib.request.urlopen(req, timeout=5) as response:
            payload = json.loads(response.read().decode("utf-8"))
        return {
            "configured": True,
            "reachable": True,
            "username": _clean(payload.get("username")) or None,
            "invite_url": invite or None,
        }
    except Exception as exc:
        return {
            "configured": True,
            "reachable": False,
            "invite_url": invite or None,
            "error": type(exc).__name__,
        }


def install_platform_status(app, require_current_user=None):
    if app is None or require_current_user is None:
        raise RuntimeError("platform status patch requires app and auth dependency")

    @app.get("/api/platforms/status")
    def platform_status():
        # This endpoint is intentionally authenticated. It reports configuration/
        # reachability only; credentials are never returned to the browser.
        require_current_user()
        telegram = _telegram_status()
        discord = _discord_status()
        return {
            "status": "ok",
            "telegram": telegram,
            "discord": discord,
        }

    print("PLATFORM_STATUS_PATCH_INSTALLED", flush=True)
