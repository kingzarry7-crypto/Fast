import sqlite3
import unittest

from kitty_watch_state import (
    all_recipients_delivered,
    ensure_delivery_table,
    is_delivered,
    mark_delivered,
)


class KittyWatchDeliveryStateTests(unittest.TestCase):
    def setUp(self):
        self.conn = sqlite3.connect(":memory:")
        ensure_delivery_table(self.conn)

    def tearDown(self):
        self.conn.close()

    def test_delivery_is_scoped_to_symbol_candle_and_recipient(self):
        self.assertFalse(is_delivered(self.conn, "BTC/USDT", "candle-1", "123"))
        mark_delivered(self.conn, "BTC/USDT", "candle-1", "123")
        self.assertTrue(is_delivered(self.conn, "BTC/USDT", "candle-1", "123"))
        self.assertFalse(is_delivered(self.conn, "BTC/USDT", "candle-2", "123"))
        self.assertFalse(is_delivered(self.conn, "XAU/USD", "candle-1", "123"))
        self.assertFalse(is_delivered(self.conn, "BTC/USDT", "candle-1", "456"))

    def test_partial_delivery_can_retry_missing_recipient(self):
        mark_delivered(self.conn, "XAU/USD", "candle-1", "123")
        self.assertFalse(
            all_recipients_delivered(
                self.conn, "XAU/USD", "candle-1", ["123", "456"]
            )
        )
        mark_delivered(self.conn, "XAU/USD", "candle-1", "456")
        self.assertTrue(
            all_recipients_delivered(
                self.conn, "XAU/USD", "candle-1", ["123", "456"]
            )
        )

    def test_mark_is_idempotent(self):
        mark_delivered(self.conn, "BTC/USDT", "candle-1", "123")
        mark_delivered(self.conn, "BTC/USDT", "candle-1", "123")
        count = self.conn.execute(
            "SELECT COUNT(*) FROM kitty_watch_deliveries"
        ).fetchone()[0]
        self.assertEqual(count, 1)


if __name__ == "__main__":
    unittest.main()
