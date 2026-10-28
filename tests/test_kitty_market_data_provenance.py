import unittest

from fetch_kitty_5m_market_data import BTC_SOURCE_NAME, XAUUSD_SOURCE_NAME


class KittyMarketDataProvenanceTests(unittest.TestCase):
    def test_btc_source_label_matches_actual_coinbase_endpoint(self):
        self.assertEqual(BTC_SOURCE_NAME, "Coinbase Exchange BTC-USD spot")
        self.assertIn("BTC-USD", BTC_SOURCE_NAME)
        self.assertNotIn("Binance", BTC_SOURCE_NAME)
        self.assertNotIn("BTCUSDT", BTC_SOURCE_NAME)

    def test_gold_source_label_identifies_twelve_data_spot(self):
        self.assertEqual(XAUUSD_SOURCE_NAME, "Twelve Data XAU/USD spot")


if __name__ == "__main__":
    unittest.main()
