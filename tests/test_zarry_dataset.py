import unittest
from datetime import datetime, timedelta, timezone
import tempfile
from pathlib import Path

from zarry_dataset import (
    build_feature_dataset,
    build_feature_dataset_from_csv,
    chronological_split,
    normalize_asset,
    validate_paper_trade_rows,
)


class ZarryDatasetTests(unittest.TestCase):
    def test_csv_builder_reads_artifact_and_preserves_provenance(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "btc.csv"
            path.write_text("timestamp,target,data_source,close\n2026-01-01T00:00:00Z,2,feed,50000\n", encoding="utf-8")
            rows = build_feature_dataset_from_csv("BTCUSD", path, "actions://artifact-1")
        self.assertEqual(rows[0]["features"]["close"], 50000.0)
        self.assertEqual(rows[0]["provenance"], "actions://artifact-1")

    def test_feature_rows_keep_forward_labels_distinct_from_paper_outcomes(self):
        rows = [
            {"timestamp": "2026-01-01T00:00:00Z", "target": "2",
             "forward_return_6h": "0.01", "data_source": "Twelve Data"},
            {"timestamp": "2026-01-01T01:00:00Z", "target": "1",
             "forward_return_6h": "0.00", "data_source": "Twelve Data"},
        ]
        result = build_feature_dataset("BTC/USD", rows, "artifact://btc.csv")
        self.assertEqual(result[0]["label_type"], "forward_price_proxy")
        self.assertNotIn("realized_net_return", result[0])
        self.assertNotIn("forward_return_6h", result[0]["features"])
        self.assertEqual(result[0]["label"], "LONG")

    def test_asset_aliases_are_normalized_and_mixed_assets_rejected(self):
        self.assertEqual(normalize_asset("XAU/USD"), "XAUUSD")
        with self.assertRaises(ValueError):
            build_feature_dataset("BTC/USD", [
                {"timestamp": "2026-01-01T00:00:00Z", "symbol": "XAUUSD",
                 "target": "2", "data_source": "test"}
            ], "artifact://mixed.csv")

    def test_chronological_split_purges_boundary_rows(self):
        rows = [{"timestamp": (datetime(2026, 1, 1, tzinfo=timezone.utc) + timedelta(hours=i)).isoformat(), "i": i}
                for i in range(100)]
        split = chronological_split(rows, purge_rows=2)
        self.assertLess(max(r["timestamp"] for r in split["train"]),
                        min(r["timestamp"] for r in split["validation"]))
        self.assertLess(max(r["timestamp"] for r in split["validation"]),
                        min(r["timestamp"] for r in split["test"]))
        self.assertEqual(split["purged_rows"], 8)

    def test_paper_outcomes_require_closed_trade_and_net_return(self):
        valid = [{"asset": "BTCUSD", "status": "closed", "mode": "paper",
                  "provenance": "paper-ledger://run-1",
                  "realized_net_return": "-0.002", "trade_id": "t1",
                  "closed_at": "2026-01-01T06:00:00Z"}]
        normalized = validate_paper_trade_rows(valid)
        self.assertEqual(normalized[0]["outcome"], "LOSS")
        with self.assertRaises(ValueError):
            validate_paper_trade_rows([{"asset": "BTCUSD", "status": "open"}])

    def test_feature_dataset_rejects_duplicate_timestamps(self):
        row = {"timestamp": "2026-01-01T00:00:00Z", "target": "2",
               "data_source": "test"}
        with self.assertRaises(ValueError):
            build_feature_dataset("BTCUSD", [row, dict(row)], "artifact://dup.csv")

    def test_non_finite_numeric_features_are_rejected(self):
        for value in ("NaN", "inf", "-inf"):
            with self.subTest(value=value):
                row = {"timestamp": "2026-01-01T00:00:00Z", "target": "2",
                       "data_source": "test", "close": value}
                with self.assertRaises(ValueError):
                    build_feature_dataset("BTCUSD", [row], "artifact://btc.csv")

    def test_paper_outcomes_require_explicit_mode_and_provenance(self):
        base = {"asset": "BTCUSD", "status": "closed", "trade_id": "t1",
                "closed_at": "2026-01-01T06:00:00Z",
                "realized_net_return": "0.01"}
        with self.assertRaisesRegex(ValueError, "explicitly verified"):
            validate_paper_trade_rows([{**base, "provenance": "ledger://1"}])
        with self.assertRaisesRegex(ValueError, "provenance"):
            validate_paper_trade_rows([{**base, "mode": "paper"}])
        accepted = validate_paper_trade_rows([
            {**base, "mode": "paper", "provenance": "ledger://1"}
        ])
        self.assertEqual(accepted[0]["provenance"], "ledger://1")


if __name__ == "__main__":
    unittest.main()
