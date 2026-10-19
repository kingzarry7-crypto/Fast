import tempfile
import unittest
from pathlib import Path

import numpy as np
import pandas as pd
import torch

import train_kitty_v3_retrained as kitty


class KittyTrainingExperimentTests(unittest.TestCase):
    def test_dataset_loader_orders_timestamps_and_accepts_named_labels(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "data.csv"
            rows = []
            for i in range(120):
                row = {feature: float(i + j) for j, feature in enumerate(kitty.FEATURES)}
                row["timestamp"] = pd.Timestamp("2024-01-01", tz="UTC") + pd.Timedelta(hours=i)
                row["target"] = ("SHORT", "NO TRADE", "LONG")[i % 3]
                rows.append(row)
            # Reverse source row order so the loader must sort by timestamp.
            pd.DataFrame(rows[::-1]).to_csv(path, index=False)
            x, y, digest = kitty.load_dataset(path)
            self.assertEqual(x.shape, (120, 18))
            self.assertEqual(set(y.tolist()), {0, 1, 2})
            self.assertEqual(len(digest), 64)
            self.assertLess(x[0, 0], x[-1, 0])

    def test_split_is_chronological_and_has_three_partitions(self):
        x = np.arange(120 * 18, dtype=np.float32).reshape(120, 18)
        y = np.arange(120, dtype=np.int64) % 3
        train, validation, test = kitty.split_chronologically(x, y)
        self.assertEqual([len(train[0]), len(validation[0]), len(test[0])], [84, 18, 18])
        self.assertLess(train[0][-1, 0], validation[0][0, 0])
        self.assertLess(validation[0][-1, 0], test[0][0, 0])


    def test_chronological_split_purges_overlapping_forward_labels(self):
        x = np.arange(300 * 18, dtype=np.float32).reshape(300, 18)
        y = np.arange(300, dtype=np.int64) % 3
        train, validation, test = kitty.split_chronologically(x, y, purge=6)
        self.assertEqual(len(train[0]), 204)
        self.assertEqual(len(validation[0]), 39)
        self.assertEqual(len(test[0]), 45)
        self.assertLess(train[0][-1, 0], validation[0][0, 0])
        self.assertLess(validation[0][-1, 0], test[0][0, 0])

    def test_paper_return_evaluation_subtracts_costs_and_skips_no_trade(self):
        class FixedModel(torch.nn.Module):
            def forward(self, x):
                return torch.tensor([[0.9, 0.05, 0.05], [0.05, 0.9, 0.05], [0.05, 0.05, 0.9]], dtype=torch.float32)
        result = kitty.evaluate_paper_returns(
            FixedModel(), np.zeros((3, 18), dtype=np.float32),
            np.asarray([-0.01, 0.02, 0.01]), round_trip_cost=0.001,
        )
        self.assertEqual(result["trade_count"], 1)
        self.assertAlmostEqual(result["win_rate"], 1.0)
        self.assertAlmostEqual(result["average_net_return"], 0.009)

    def test_six_hour_paper_trades_do_not_overlap(self):
        class AlwaysLong(torch.nn.Module):
            def forward(self, x):
                logits = torch.tensor([0.01, 0.01, 0.99], dtype=torch.float32)
                return logits.repeat(len(x), 1)

        result = kitty.evaluate_paper_returns(
            AlwaysLong(), np.zeros((12, 18), dtype=np.float32),
            np.full(12, 0.01, dtype=np.float64), round_trip_cost=0.001,
        )
        # Signals at indices 0 and 6 are eligible; indices 1..5 overlap
        # the first trade's next-open entry and six-hour holding period.
        self.assertEqual(result["trade_count"], 2)
        self.assertEqual(result["skipped_overlapping_signals"], 10)

    def test_training_tracks_learning_rate_for_scheduler(self):
        rng = np.random.default_rng(7)
        x_train = rng.normal(size=(84, 18)).astype(np.float32)
        y_train = np.arange(84, dtype=np.int64) % 3
        x_val = rng.normal(size=(18, 18)).astype(np.float32)
        y_val = np.arange(18, dtype=np.int64) % 3
        _, training = kitty.train_one(
            x_train, y_train, x_val, y_val,
            variant="baseline", optimizer_name="adamw", seed=7,
            epochs=3, patience=2, batch_size=32, weight_decay=1e-4,
        )
        self.assertGreaterEqual(training["best_epoch"], 1)
        self.assertTrue(training["history"])
        self.assertTrue(all("learning_rate" in item for item in training["history"]))
        self.assertTrue(all(item["learning_rate"] > 0 for item in training["history"]))

    def test_architecture_variants_return_three_class_logits(self):
        for variant in ("baseline", "batchnorm", "leaky_relu"):
            model = kitty.KittyExperimentNet(variant=variant)
            model.eval()
            with torch.inference_mode():
                output = model(torch.zeros(4, 18))
            self.assertEqual(tuple(output.shape), (4, 3))


if __name__ == "__main__":
    unittest.main()
