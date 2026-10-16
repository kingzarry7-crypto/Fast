import unittest
from unittest.mock import patch
import news


class CalendarLiveHealthStatusTests(unittest.TestCase):
    def test_configured_keys_do_not_prove_calendar_is_live(self):
        with patch.object(news, "EODHD_API_KEY", "configured"), patch.object(
            news, "TRADING_ECONOMICS_API_KEY", ""
        ), patch.object(news, "FINNHUB_API_KEY", ""), patch.object(
            news, "TWELVE_DATA_API_KEY", ""
        ), patch.object(news.NewsEngineSingleton, "_instance", None):
            status = news.provider_status()
        self.assertTrue(status["calendar_configured_flag"])
        self.assertFalse(status["calendar_available"])


if __name__ == "__main__":
    unittest.main()
