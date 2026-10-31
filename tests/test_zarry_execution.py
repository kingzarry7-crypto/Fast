import unittest

from zarry_execution import simulate_non_overlapping_trades


class SharedExecutionTests(unittest.TestCase):
    def test_signal_on_prior_exit_candle_is_eligible(self):
        result = simulate_non_overlapping_trades(
            forward_returns=[0.01] * 15,
            directions=[1, 0, 0, 0, 0, 0, 0, -1, 0, 0, 0, 0, 0, 0, 0],
            round_trip_cost=0.001,
            outcome_horizon_rows=7,
        )
        self.assertEqual(result["trade_count"], 2)
        self.assertEqual(result["trade_indices"], [
            {"entry_index": 0, "exit_index": 7},
            {"entry_index": 7, "exit_index": 14},
        ])
        self.assertAlmostEqual(result["compounded_net_return"], (1.009 * 0.989) - 1.0)

    def test_overlapping_signals_and_incomplete_outcomes_are_counted(self):
        result = simulate_non_overlapping_trades(
            forward_returns=[0.01] * 10,
            directions=[1, 1, 0, 0, 0, 0, 0, 0, 1, 0],
            round_trip_cost=0.001,
            outcome_horizon_rows=7,
        )
        self.assertEqual(result["trade_count"], 1)
        self.assertEqual(result["skipped_overlapping_signals"], 1)
        self.assertEqual(result["skipped_incomplete_outcomes"], 1)

    def test_costs_and_drawdown_match_compounded_trade_sequence(self):
        result = simulate_non_overlapping_trades(
            forward_returns=[-0.01] + [0.0] * 6 + [0.02] + [0.0] * 7,
            directions=[1] + [0] * 6 + [1] + [0] * 7,
            round_trip_cost=0.001,
            outcome_horizon_rows=7,
        )
        self.assertAlmostEqual(result["net_trade_returns"][0], -0.011)
        self.assertAlmostEqual(result["net_trade_returns"][1], 0.019)
        self.assertAlmostEqual(result["compounded_net_return"], (0.989 * 1.019) - 1.0)
        self.assertAlmostEqual(result["max_drawdown"], 0.011)


if __name__ == "__main__":
    unittest.main()
