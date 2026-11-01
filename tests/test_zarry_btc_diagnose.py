import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "research-data" / "scripts"))

from zarry_btc_diagnose import EXPECTED_CSV_SHA256, verify_btc_dataset


class BTCArtifactContractTests(unittest.TestCase):
    def test_runner_pins_the_verified_run106_btc_dataset_hash(self):
        self.assertEqual(
            EXPECTED_CSV_SHA256,
            "c4c017a7a32ed98c3a336e92c33e51bd9a489fe403e003a89bee6623a58674d5",
        )

    def test_rejects_any_dataset_that_does_not_match_the_archive(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "hourly_features.csv"
            path.write_text("not the archived BTC dataset", encoding="utf-8")
            with self.assertRaisesRegex(ValueError, "BTCUSD CSV hash mismatch"):
                verify_btc_dataset(path)


if __name__ == "__main__":
    unittest.main()
