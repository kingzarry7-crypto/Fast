import os
import unittest
from unittest.mock import Mock, patch

import market


class EulerpoolGoldReferenceTests(unittest.TestCase):
    @patch.dict(os.environ, {"EULERPOOL_API_KEY": "test-key"})
    @patch("market.requests.get")
    def test_reads_latest_valid_daily_gold_price_with_bearer_auth(self, get):
        response = Mock()
        response.status_code = 200
        response.json.return_value = [
            {"symbol": "GOLD", "date": "2026-10-20T00:00:00.000Z", "price": 4010.5},
            {"symbol": "GOLD", "date": "2026-10-22T00:00:00.000Z", "price": 4022.75},
            {"symbol": "GOLD", "date": "2026-10-21T00:00:00.000Z", "price": None},
        ]
        get.return_value = response

        price = market._eulerpool_gold_get_price()

        self.assertEqual(price, 4022.75)
        args, kwargs = get.call_args
        self.assertEqual(args[0], "https://api.eulerpool.com/api/1/commodity/prices/GOLD")
        self.assertEqual(kwargs["headers"]["Authorization"], "Bearer test-key")
        self.assertEqual(kwargs["params"], {"days": 30})

    @patch.dict(os.environ, {}, clear=True)
    def test_missing_key_fails_closed(self):
        with self.assertRaisesRegex(RuntimeError, "EULERPOOL_API_KEY"):
            market._eulerpool_gold_get_price()

    @patch.dict(os.environ, {"EULERPOOL_API_KEY": "test-key"})
    @patch("market.requests.get")
    def test_rejects_empty_or_invalid_payload(self, get):
        response = Mock()
        response.status_code = 200
        response.json.return_value = [{"symbol": "GOLD", "date": "2026-10-22", "price": 0}]
        get.return_value = response
        with self.assertRaisesRegex(RuntimeError, "no valid prices"):
            market._eulerpool_gold_get_price()


if __name__ == "__main__":
    unittest.main()
