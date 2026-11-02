import unittest
from datetime import datetime, timedelta, timezone

from kitty_api import _validate_candles


TIMEFRAME_LIMITS = {
    "1m": (timedelta(minutes=1), timedelta(minutes=5)),
    "5m": (timedelta(minutes=5), timedelta(minutes=15)),
    "15m": (timedelta(minutes=15), timedelta(minutes=45)),
    "30m": (timedelta(minutes=30), timedelta(minutes=90)),
    "1h": (timedelta(hours=1), timedelta(hours=3)),
    "2h": (timedelta(hours=2), timedelta(hours=6)),
    "4h": (timedelta(hours=4), timedelta(hours=12)),
    "1d": (timedelta(days=1), timedelta(days=3)),
}


def make_candles(timeframe, latest_age):
    interval, _ = TIMEFRAME_LIMITS[timeframe]
    latest = datetime.now(timezone.utc).replace(microsecond=0) - latest_age
    candles = []
    for index in range(40):
        stamp = latest - interval * (39 - index)
        close = 100.0 + index / 100.0
        candles.append({
            "datetime": stamp.isoformat(),
            "open": close,
            "high": close + 0.1,
            "low": close - 0.1,
            "close": close,
        })
    return candles


class KittyTimeframeFreshnessTests(unittest.TestCase):
    def test_each_supported_timeframe_rejects_data_older_than_its_own_limit(self):
        for timeframe, (_, max_age) in TIMEFRAME_LIMITS.items():
            with self.subTest(timeframe=timeframe):
                candles = make_candles(timeframe, max_age + timedelta(minutes=1))
                with self.assertRaisesRegex(ValueError, "stale or future candle"):
                    _validate_candles(candles, timeframe, "BTC/USDT")

    def test_each_supported_timeframe_accepts_recent_timestamped_candles(self):
        for timeframe in TIMEFRAME_LIMITS:
            with self.subTest(timeframe=timeframe):
                candles = make_candles(timeframe, timedelta(minutes=1))
                result = _validate_candles(candles, timeframe, "BTC/USDT")
                self.assertTrue(result.endswith("+00:00"))

    def test_each_supported_timeframe_accepts_data_within_its_own_limit(self):
        for timeframe, (_, max_age) in TIMEFRAME_LIMITS.items():
            with self.subTest(timeframe=timeframe):
                candles = make_candles(timeframe, max_age - timedelta(minutes=1))
                _validate_candles(candles, timeframe, "BTC/USDT")

    def test_unknown_timeframe_fails_closed(self):
        candles = make_candles("1h", timedelta(minutes=1))
        with self.assertRaisesRegex(ValueError, "unsupported timeframe"):
            _validate_candles(candles, "3h", "BTC/USDT")


if __name__ == "__main__":
    unittest.main()
