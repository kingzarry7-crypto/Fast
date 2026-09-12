"""Environment-backed configuration shared by the bot modules."""
import os


def _env_int(name: str, default: int, minimum: int, maximum: int) -> int:
    try:
        value = int(os.getenv(name, str(default)))
    except (TypeError, ValueError):
        return default
    return max(minimum, min(value, maximum))

# Existing configuration values are intentionally preserved.
TWELVE_DATA_URL = "https://api.twelvedata.com"
TTS_VOICE_ID = os.getenv("TTS_VOICE_ID", "").strip() or None
ANALYSIS_DEFAULT_TIMEFRAME = os.getenv("ANALYSIS_DEFAULT_TIMEFRAME", "1h").strip() or "1h"
ANALYSIS_LOOKBACK_BARS = _env_int("ANALYSIS_LOOKBACK_BARS", 120, 60, 1000)
ANALYSIS_NEWS_LOOKBACK_HOURS = _env_int("ANALYSIS_NEWS_LOOKBACK_HOURS", 24, 1, 168)
ANALYSIS_UPCOMING_NEWS_HOURS = _env_int("ANALYSIS_UPCOMING_NEWS_HOURS", 24, 1, 168)
