import unittest
from unittest.mock import Mock, patch

import news


class ForexFactoryCalendarParserTests(unittest.TestCase):
    @patch("news.requests.get")
    def test_uses_country_field_as_currency_when_currency_is_missing(self, mock_get):
        response = Mock()
        response.status_code = 200
        response.json.return_value = [
            {
                "title": "Core CPI m/m",
                "country": "USD",
                "date": "2026-10-23T08:30:00-04:00",
                "impact": "High",
                "forecast": "0.2%",
                "previous": "0.1%",
            }
        ]
        mock_get.return_value = response

        events = news.get_forexfactory_events()

        self.assertEqual(len(events), 1)
        self.assertEqual(events[0]["provider"], "FOREXFACTORY")
        self.assertEqual(events[0]["event"], "Core CPI m/m")
        self.assertEqual(events[0]["currency"], "USD")
        self.assertEqual(events[0]["impact"], "HIGH")

    @patch("news.requests.get")
    def test_explicit_currency_field_takes_precedence(self, mock_get):
        response = Mock()
        response.status_code = 200
        response.json.return_value = [
            {
                "title": "Employment Change",
                "country": "Canada",
                "currency": "USD",
                "date": "2026-10-23T08:30:00-04:00",
                "impact": "Medium",
            }
        ]
        mock_get.return_value = response

        events = news.get_forexfactory_events()

        self.assertEqual(len(events), 1)
        self.assertEqual(events[0]["currency"], "USD")


if __name__ == "__main__":
    unittest.main()
