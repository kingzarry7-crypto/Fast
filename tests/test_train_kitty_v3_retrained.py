import tempfile
import unittest
from pathlib import Path

import numpy as np
import pandas as pd
import torch

import train_kitty_v3_retrained as kitty
import kitty_v3_retrained as inference


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

        forward_returns = np.full(12, 0.01, dtype=np.float64)
        forward_returns[6] = 0.015  # Must be skipped: prior trade exits at t+7.
        forward_returns[7] = 0.02   # First eligible next signal.
        result = kitty.evaluate_paper_returns(
            AlwaysLong(), np.zeros((12, 18), dtype=np.float32),
            forward_returns, round_trip_cost=0.001,
        )
        # Signals at indices 0 and 7 are eligible; indices 1..6 overlap
        # the first trade's next-open entry through its t+7 exit candle.
        self.assertEqual(result["trade_count"], 2)
        self.assertEqual(result["skipped_overlapping_signals"], 10)
        self.assertAlmostEqual(result["average_net_return"], 0.014)

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

    def test_confidence_selection_disables_signals_when_validation_edge_is_negative(self):
        trials = [
            {"min_confidence": 0.4, "trade_count": 30, "compounded_net_return": -0.08, "average_net_return": -0.003},
            {"min_confidence": 0.5, "trade_count": 4, "compounded_net_return": 0.02, "average_net_return": 0.01},
        ]
        threshold, reason = kitty.select_confidence_threshold(trials)
        self.assertGreater(threshold, 1.0)
        self.assertIn("signals_disabled", reason)

    def test_confidence_selection_uses_profitable_validation_threshold_with_enough_trades(self):
        trials = [
            {"min_confidence": 0.4, "trade_count": 30, "compounded_net_return": 0.02, "average_net_return": 0.001, "max_drawdown": -0.03, "profit_factor": 1.2},
            {"min_confidence": 0.5, "trade_count": 20, "compounded_net_return": 0.04, "average_net_return": 0.002, "max_drawdown": -0.01, "profit_factor": 1.2},
            {"min_confidence": 0.6, "trade_count": 2, "compounded_net_return": 0.10, "average_net_return": 0.05},
        ]
        threshold, reason = kitty.select_confidence_threshold(trials)
        self.assertEqual(threshold, 0.4)
        self.assertIn("best_validation", reason)

    def test_holdout_gate_disables_signals_when_net_returns_are_negative(self):
        holdout = {"trade_count": 17, "average_net_return": -0.0076, "compounded_net_return": -0.1239}
        self.assertTrue(kitty.should_disable_signals(0.5, holdout))

    def test_holdout_gate_disables_signals_when_trade_sample_is_too_small(self):
        holdout = {"trade_count": 7, "average_net_return": 0.01, "compounded_net_return": 0.05}
        self.assertTrue(kitty.should_disable_signals(0.5, holdout))

    def test_holdout_gate_allows_only_enough_positive_net_trades(self):
        holdout = {"trade_count": 35, "average_net_return": 0.001, "compounded_net_return": 0.02, "max_drawdown": -0.03, "profit_factor": 1.2}
        self.assertFalse(kitty.should_disable_signals(0.5, holdout))
        self.assertTrue(kitty.should_disable_signals(1.01, holdout))

    def test_holdout_gate_disables_signals_when_profit_factor_is_below_minimum(self):
        holdout = {"trade_count": 35, "average_net_return": 0.001, "compounded_net_return": 0.02, "max_drawdown": -0.03, "profit_factor": 1.05}
        self.assertTrue(kitty.should_disable_signals(0.5, holdout))

    def test_holdout_gate_disables_signals_when_profit_factor_is_missing(self):
        holdout = {"trade_count": 35, "average_net_return": 0.001, "compounded_net_return": 0.02, "max_drawdown": -0.03}
        self.assertTrue(kitty.should_disable_signals(0.5, holdout))

    def test_inference_gate_blocks_missing_or_unverified_broker_spread(self):
        checkpoint = {
            "production_ready": True,
            "broker_spread_verified": False,
            "recommended_min_confidence": 0.4,
            "test_metrics": {
                "signals_disabled_for_no_validated_edge": False,
                "paper_backtest_after_assumed_costs": {
                    "trade_count": 35, "average_net_return": 0.01,
                    "compounded_net_return": 0.03, "max_drawdown": -0.02,
                    "profit_factor": 1.2,
                },
            },
        }
        signal, reason = inference.apply_research_signal_gate("LONG", 0.99, checkpoint)
        self.assertEqual(signal, "NO TRADE")
        self.assertEqual(reason, "broker_spread_not_verified")
        checkpoint["broker_spread_verified"] = True
        signal, _ = inference.apply_research_signal_gate("LONG", 0.99, checkpoint)
        self.assertEqual(signal, "LONG")

    def test_inference_gate_blocks_unapproved_checkpoint(self):
        signal, reason = inference.apply_research_signal_gate(
            "LONG", 0.9, {"production_ready": False, "recommended_min_confidence": 0.4}
        )
        self.assertEqual(signal, "NO TRADE")
        self.assertEqual(reason, "checkpoint_not_approved_for_production")

    def test_inference_gate_blocks_holdout_with_no_validated_edge(self):
        checkpoint = {
            "production_ready": True,
            "broker_spread_verified": True,
            "recommended_min_confidence": 0.4,
            "test_metrics": {"signals_disabled_for_no_validated_edge": True},
        }
        signal, reason = inference.apply_research_signal_gate("SHORT", 0.9, checkpoint)
        self.assertEqual(signal, "NO TRADE")
        self.assertEqual(reason, "holdout_validation_found_no_positive_net_edge")

    def test_inference_gate_requires_validated_confidence_threshold(self):
        checkpoint = {"production_ready": True,
            "broker_spread_verified": True, "recommended_min_confidence": 1.01, "test_metrics": {}}
        signal, reason = inference.apply_research_signal_gate("LONG", 0.9, checkpoint)
        self.assertEqual(signal, "NO TRADE")
        self.assertEqual(reason, "no_validated_confidence_threshold")

    def test_candidate_selection_prefers_positive_net_validation_returns_after_costs(self):
        trials = [
            {"candidate_id": "high-f1-but-losing", "min_confidence": 0.5,
             "trade_count": 30, "average_net_return": -0.001,
             "compounded_net_return": -0.03, "max_drawdown": -0.05},
            {"candidate_id": "positive-net", "min_confidence": 0.6,
             "trade_count": 35, "average_net_return": 0.002,
             "compounded_net_return": 0.04, "max_drawdown": -0.02, "profit_factor": 1.2},
            {"candidate_id": "too-few-trades", "min_confidence": 0.4,
             "trade_count": 4, "average_net_return": 0.02,
             "compounded_net_return": 0.08, "max_drawdown": -0.01},
        ]
        selected = kitty.select_validation_candidate(trials)
        self.assertEqual(selected["candidate_id"], "positive-net")

    def test_candidate_selection_returns_none_when_no_validation_edge_exists(self):
        trials = [
            {"min_confidence": 0.5, "trade_count": 30,
             "average_net_return": -0.001, "compounded_net_return": -0.03},
            {"min_confidence": 0.4, "trade_count": 5,
             "average_net_return": 0.01, "compounded_net_return": 0.04},
        ]
        self.assertIsNone(kitty.select_validation_candidate(trials))

    def test_inference_gate_rejects_approval_flag_without_positive_after_cost_metrics(self):
        checkpoint = {
            "production_ready": True,
            "broker_spread_verified": True,
            "recommended_min_confidence": 0.4,
            "test_metrics": {"signals_disabled_for_no_validated_edge": False},
        }
        signal, reason = inference.apply_research_signal_gate("LONG", 0.99, checkpoint)
        self.assertEqual(signal, "NO TRADE")
        self.assertEqual(reason, "holdout_validation_metrics_incomplete_or_unprofitable")

    def test_inference_gate_rejects_too_few_holdout_trades(self):
        checkpoint = {
            "production_ready": True,
            "broker_spread_verified": True,
            "recommended_min_confidence": 0.4,
            "test_metrics": {
                "signals_disabled_for_no_validated_edge": False,
                "paper_backtest_after_assumed_costs": {
                    "trade_count": 35,
                    "average_net_return": 0.01,
                    "compounded_net_return": 0.03,
                    "max_drawdown": -0.07,
                },
            },
        }
        signal, reason = inference.apply_research_signal_gate("LONG", 0.99, checkpoint)
        self.assertEqual(signal, "NO TRADE")
        self.assertEqual(reason, "holdout_validation_metrics_incomplete_or_unprofitable")

    def test_architecture_variants_return_three_class_logits(self):
        for variant in ("baseline", "batchnorm", "leaky_relu"):
            model = kitty.KittyExperimentNet(variant=variant)
            model.eval()
            with torch.inference_mode():
                output = model(torch.zeros(4, 18))
            self.assertEqual(tuple(output.shape), (4, 3))


if __name__ == "__main__":
    unittest.main()
