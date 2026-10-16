"""Tests that Twelve Data is not misused as a macroeconomic calendar provider."""
import unittest
from unittest.mock import patch

import news


class TwelveDataCalendarRoutingTests(unittest.TestCase):
    def test_news_provider_twelvedata_does_not_select_calendar_endpoint(self):
        with (
            patch.object(news, "CALENDAR_PROVIDER", "AUTO"),
            patch.object(news, "NEWS_PROVIDER", "TWELVEDATA"),
            patch.object(news, "EODHD_API_KEY", ""),
            patch.object(news, "TRADING_ECONOMICS_API_KEY", ""),
            patch.object(news, "FINNHUB_API_KEY", ""),
            patch.object(news, "TWELVE_DATA_API_KEY", "configured-key"),
        ):
            self.assertEqual(news.get_available_calendar_provider(), "FOREXFACTORY")

    def test_explicit_twelvedata_calendar_configuration_fails_clearly(self):
        with (
            patch.object(news, "CALENDAR_PROVIDER", "TWELVEDATA"),
            patch.object(news, "TWELVE_DATA_API_KEY", "configured-key"),
        ):
            with self.assertRaisesRegex(RuntimeError, "not a supported macroeconomic-calendar provider"):
                news.get_available_calendar_provider()

    def test_twelvedata_is_not_reported_as_calendar_capability(self):
        with patch.object(news, "TWELVE_DATA_API_KEY", "configured-key"):
            status = news.provider_status()

        self.assertNotIn("twelvedata", status["calendar_keyed_configured"])
        self.assertNotIn("twelvedata", status["calendar_configured"])

    def test_explicit_twelvedata_event_fetch_fails_without_network_request(self):
        with self.assertRaisesRegex(RuntimeError, "not a supported macroeconomic-calendar provider"):
            news.get_economic_events(provider="TWELVEDATA")


if __name__ == "__main__":
    unittest.main()
