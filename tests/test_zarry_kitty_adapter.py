import csv
import tempfile
import unittest
from pathlib import Path

from zarry_kitty_adapter import KITTY_FEATURES, adapt_kitty_hourly_csv


def write_fixture(path: Path, asset="BTC", source="Binance public klines"):
    columns = ["timestamp", *KITTY_FEATURES, "entry_price_next_open",
               "exit_price_after_6h", "forward_return_6h", "target", "data_source"]
    values = {
        "timestamp": "2026-01-01T00:00:00Z",
        "entry_price_next_open": "100",
        "exit_price_after_6h": "101",
        "forward_return_6h": "0.01",
        "target": "2",
        "data_source": source,
    }
    values.update({name: "0.1" for name in KITTY_FEATURES})
    with path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=columns)
        writer.writeheader()
        writer.writerow(values)


class ZarryKittyAdapterTests(unittest.TestCase):
    def test_btc_csv_creates_manifest_and_preserves_forward_label_type(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "btc.csv"
            write_fixture(path)
            rows, manifest = adapt_kitty_hourly_csv("BTCUSD", path)
        self.assertEqual(len(rows), 1)
        self.assertEqual(manifest["asset"], "BTCUSD")
        self.assertEqual(manifest["label_type"], "forward_price_proxy")
        self.assertEqual(manifest["purge_rows_per_boundary"], 7)
        self.assertFalse(manifest["realized_paper_outcomes_included"])
        self.assertEqual(rows[0]["provenance"], "sha256:" + manifest["source_file_sha256"])

    def test_btc_accepts_actual_yahoo_finance_fallback_artifact_provenance(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "btc.csv"
            write_fixture(path, source="Yahoo Finance fallback")
            rows, manifest = adapt_kitty_hourly_csv("BTCUSD", path)
        self.assertEqual(len(rows), 1)
        self.assertEqual(manifest["market_data_sources"], ["Yahoo Finance fallback"])

    def test_gold_requires_real_twelve_data_spot_provenance(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "gold.csv"
            write_fixture(path, "XAUUSD", "Yahoo Finance GC=F futures proxy")
            with self.assertRaisesRegex(ValueError, "Twelve Data"):
                adapt_kitty_hourly_csv("XAUUSD", path)
            write_fixture(path, "XAUUSD", "Twelve Data XAU/USD spot")
            _, manifest = adapt_kitty_hourly_csv("XAUUSD", path)
        self.assertEqual(manifest["market_data_sources"], ["Twelve Data XAU/USD spot"])

    def test_rejects_inconsistent_forward_return(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "btc.csv"
            write_fixture(path)
            text = path.read_text().replace(",0.01,2,", ",0.02,2,")
            path.write_text(text)
            with self.assertRaisesRegex(ValueError, "does not match"):
                adapt_kitty_hourly_csv("BTCUSD", path)

    def test_rejects_missing_feature_columns(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "btc.csv"
            path.write_text("timestamp,target,data_source\n2026-01-01T00:00:00Z,2,Binance public klines\n")
            with self.assertRaisesRegex(ValueError, "missing required columns"):
                adapt_kitty_hourly_csv("BTCUSD", path)


if __name__ == "__main__":
    unittest.main()
