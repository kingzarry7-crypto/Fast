import unittest

from kitty_realistic_backtest import BacktestConfig
from run_kitty_realistic_backtest import (
    _candidate_diagnostic_summary,
    _candidate_failure_reasons,
)


def candidate(*, return_=0.02, trades=30, pf=1.3, drawdown=-0.03,
              fold_returns=(0.01, 0.02, 0.01), stress_return=0.01,
              stress_trades=30, stress_pf=1.2, stress_drawdown=-0.03,
              stress_fold_returns=(0.01, 0.01, 0.01)):
    validation = {
        "trade_count": trades,
        "compounded_net_return": return_,
        "profit_factor": pf,
        "max_drawdown": drawdown,
    }
    stress = {
        "trade_count": stress_trades,
        "compounded_net_return": stress_return,
        "profit_factor": stress_pf,
        "max_drawdown": stress_drawdown,
    }
    return {
        "strategy": "mtf_pullback",
        "direction_mode": "both",
        "config": BacktestConfig(),
        "validation": validation,
        "stress_validation": stress,
        "fold_results": [
            {"compounded_net_return": value} for value in fold_returns
        ],
        "positive_validation_folds": sum(value > 0 for value in fold_returns),
        "positive_stress_validation_folds": sum(value > 0 for value in stress_fold_returns),
    }


class KittyCandidateDiagnosticsTests(unittest.TestCase):
    def test_eligible_candidate_has_no_failure_reasons(self):
        self.assertEqual(_candidate_failure_reasons(candidate()), [])

    def test_every_failed_gate_is_named(self):
        item = candidate(
            return_=-0.01, trades=4, pf=0.7, drawdown=-0.08,
            fold_returns=(-0.01, 0.02, -0.03),
            stress_return=-0.02, stress_trades=3, stress_pf=0.5,
            stress_drawdown=-0.09, stress_fold_returns=(-0.01, 0.0, -0.02),
        )
        reasons = _candidate_failure_reasons(item)
        self.assertIn("validation_trade_count_below_20", reasons)
        self.assertIn("validation_return_not_positive", reasons)
        self.assertIn("validation_profit_factor_below_1_10", reasons)
        self.assertIn("validation_drawdown_below_minus_5_percent", reasons)
        self.assertIn("fewer_than_3_positive_validation_folds", reasons)
        self.assertIn("stress_trade_count_below_20", reasons)
        self.assertIn("stress_return_not_positive", reasons)
        self.assertIn("stress_profit_factor_below_1_10", reasons)
        self.assertIn("stress_drawdown_below_minus_5_percent", reasons)
        self.assertIn("fewer_than_3_positive_stress_folds", reasons)

    def test_summary_counts_failures_and_ranks_near_misses_without_holdout(self):
        weak = candidate(return_=-0.01, fold_returns=(-0.01, -0.01, 0.0))
        strong = candidate()
        report = _candidate_diagnostic_summary([weak, strong], limit=2)
        self.assertEqual(report["computed_from"], "validation_only")
        self.assertFalse(report["holdout_used"])
        self.assertEqual(len(report["near_miss_candidates"]), 2)
        self.assertEqual(report["near_miss_candidates"][0]["failure_reasons"], [])
        self.assertGreater(
            report["gate_failure_counts"]["validation_return_not_positive"], 0
        )
        self.assertNotIn("holdout_return", str(report).lower())


if __name__ == "__main__":
    unittest.main()
