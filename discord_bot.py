print("🇳🇬 DISCORDBOT-V3-LOADED 🇳🇬", flush=True)
print("🔵 BOOT: discord_bot bootstrap + market_intent fix...", flush=True)
import urllib.request
_URL = "https://raw.githubusercontent.com/kingzarry7-crypto/Fast/90c672f0de1017ee08d7d8ec3be61278b7bdd596/discord_bot.py"
_src = urllib.request.urlopen(_URL, timeout=90).read().decode("utf-8")
exec(compile(_src, "discord_bot_restored.py", "exec"), globals())
try:
    from market_intent import detect_market_intent as _mi
    def detect_market_intent_discord(text: str):
        return _mi(text)
    print("🔵 BOOT: discord market_intent override applied", flush=True)
except Exception as _e:
    print(f"🔵 BOOT: discord market_intent override skipped: {_e}", flush=True)
