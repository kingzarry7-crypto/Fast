print("🇳🇬 BOTPY-V3-NEW-LOADED 🇳🇬", flush=True)
print("🔵 BOOT: bot.py + slash-only market_intent...", flush=True)
import urllib.request

_URLS = [
    "https://raw.githubusercontent.com/kingzarry7-crypto/Fast/5382b6b72f4f02df3e182bc742d2b9345d4a347d/bot.py",
]
_src = None
for u in _URLS:
    try:
        _src = urllib.request.urlopen(u, timeout=90).read().decode("utf-8")
        if len(_src) > 50000 and "def detect_market_intent" in _src:
            print("🔵 BOOT: downloaded full bot", flush=True)
            break
    except Exception as e:
        print("🔵 BOOT: download try failed", e, flush=True)
if not _src:
    raise SystemExit("could not download full bot.py")

exec(compile(_src, "bot_restored.py", "exec"), globals())

try:
    from market_intent import detect_market_intent as _mi
    detect_market_intent = _mi
    print("🔵 BOOT: market_intent slash-only ACTIVE", flush=True)
except Exception as e:
    print("🔵 BOOT: market_intent import failed:", e, flush=True)
