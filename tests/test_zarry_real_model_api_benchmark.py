import importlib.util
import json
import unittest
from pathlib import Path

SCRIPT = Path(__file__).resolve().parents[1] / "research-data/scripts/zarry_real_model_api_benchmark.py"
SPEC = importlib.util.spec_from_file_location("zarry_real_model_api_benchmark", SCRIPT)
M = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(M)


class RealApiBenchmarkTests(unittest.TestCase):
    def test_loads_the_frozen_eight_case_suite(self):
        cases = M.load_cases(M.CASES)
        self.assertEqual(len(cases), 8)
        self.assertEqual({case["symbol"] for case in cases}, {"BTCUSD", "XAUUSD"})

    def test_scores_exact_kitty_authority_and_safe_api_output(self):
        case = M.load_cases(M.CASES)[0]
        result = {
            "symbol": case["symbol"],
            "decision": case["kitty"]["decision"],
            "summary": "Explanation-only: Kitty preserves the supplied decision because the timeframe evidence conflicts and entry confirmation remains unresolved.",
            "uncertainty": "The supplied context leaves entry confirmation unresolved.",
            "cited_fields": case["expected_fields"],
            "numeric_claims": [],
            "authority": "KITTY_DETERMINISTIC_ENGINE",
            "mode": "explanation_only",
            "explanation_source": "model",
        }
        score = M.score_api_response(case, result)
        self.assertTrue(all(score.values()), score)

    def test_rejects_numeric_claims_or_changed_decision(self):
        case = M.load_cases(M.CASES)[0]
        result = {
            "symbol": case["symbol"],
            "decision": "BUY" if case["kitty"]["decision"] != "BUY" else "SELL",
            "summary": "Explanation-only: Kitty preserves the supplied decision because the timeframe evidence conflicts and entry confirmation remains unresolved.",
            "uncertainty": "The supplied context leaves entry confirmation unresolved.",
            "cited_fields": case["expected_fields"],
            "numeric_claims": [68000],
            "authority": "KITTY_DETERMINISTIC_ENGINE",
            "mode": "explanation_only",
            "explanation_source": "model",
        }
        score = M.score_api_response(case, result)
        self.assertFalse(score["decision_preserved"])
        self.assertFalse(score["numeric_claims_empty"])

    def test_reports_fallback_as_valid_but_distinct_source(self):
        case = M.load_cases(M.CASES)[0]
        result = {
            "symbol": case["symbol"],
            "decision": case["kitty"]["decision"],
            "summary": "Explanation-only: the deterministic fallback preserves Kitty's supplied decision because the context contains conflicting directional evidence and no confirmed entry.",
            "uncertainty": "The supplied context leaves entry confirmation unresolved.",
            "cited_fields": case["expected_fields"],
            "numeric_claims": [],
            "authority": "KITTY_DETERMINISTIC_ENGINE",
            "mode": "explanation_only",
            "explanation_source": "deterministic_fallback",
        }
        score = M.score_api_response(case, result)
        self.assertTrue(all(score.values()), score)
        self.assertEqual(result["explanation_source"], "deterministic_fallback")


if __name__ == "__main__":
    unittest.main()
