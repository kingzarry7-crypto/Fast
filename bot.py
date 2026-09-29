print("🇳🇬 BOTPY-V3-NEW-LOADED 🇳🇬", flush=True)
print("🔵 BOOT: bot.py bootstrap restore...", flush=True)
import urllib.request
_URL = "https://raw.githubusercontent.com/kingzarry7-crypto/Fast/5382b6b72f4f02df3e182bc742d2b9345d4a347d/bot.py"
_src = urllib.request.urlopen(_URL, timeout=90).read().decode("utf-8")
exec(compile(_src, "bot_restored.py", "exec"), globals())
try:
    from market_intent import detect_market_intent as _detect_market_intent_v2
    detect_market_intent = _detect_market_intent_v2
    print("🔵 BOOT: market_intent override applied", flush=True)
except Exception as _e:
    print(f"🔵 BOOT: market_intent override skipped: {_e}", flush=True)
