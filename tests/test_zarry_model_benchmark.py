import importlib.util
import json
import unittest
from pathlib import Path

SCRIPT = Path(__file__).resolve().parents[1] / "research-data/scripts/zarry_model_benchmark.py"
SPEC = importlib.util.spec_from_file_location("zarry_model_benchmark", SCRIPT)
M = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(M)


class BenchmarkContractTests(unittest.TestCase):
    def test_cases_cover_both_assets_and_all_decisions(self):
        cases = M.load_cases(M.CASES)
        self.assertEqual(len(cases), 8)
        self.assertEqual({case["symbol"] for case in cases}, {"BTCUSD", "XAUUSD"})
        self.assertEqual({case["kitty"]["decision"] for case in cases}, {"BUY", "SELL", "WAIT"})

    def test_qwen_candidates_point_to_repositories_with_q4_k_m_files(self):
        self.assertEqual(M.MODELS["qwen3-0.6b"]["repo_id"], "unsloth/Qwen3-0.6B-GGUF")
        self.assertEqual(M.MODELS["qwen3-0.6b"]["pattern"], "Qwen3-0.6B-Q4_K_M.gguf")
        self.assertEqual(M.MODELS["qwen3-1.7b"]["repo_id"], "unsloth/Qwen3-1.7B-GGUF")
        self.assertEqual(M.MODELS["qwen3-1.7b"]["pattern"], "Qwen3-1.7B-Q4_K_M.gguf")

    def test_smollm3_is_not_a_benchmark_candidate_and_workflow_defaults_to_qwen(self):
        self.assertEqual(set(M.MODELS), {"qwen3-0.6b", "qwen3-1.7b"})
        root = Path(__file__).resolve().parents[1]
        workflow = (root / ".github/workflows/zarry-model-benchmark.yml").read_text()
        readme = (root / "research-data/zarry-model/README.md").read_text()
        self.assertIn('default: "qwen3-1.7b"', workflow)
        self.assertNotIn("smollm3-3b", workflow)
        self.assertNotIn("SmolLM3", readme)

    def test_parse_accepts_exact_schema(self):
        value = {
            "symbol": "BTCUSD",
            "decision": "WAIT",
            "summary": "Explanation-only.",
            "uncertainty": "Conflict.",
            "cited_fields": ["trend_4h"],
            "numeric_claims": [],
        }
        self.assertEqual(M.parse_output(json.dumps(value)), value)

    def test_parse_rejects_extra_keys_and_invalid_decisions(self):
        value = {
            "symbol": "BTCUSD",
            "decision": "WAIT",
            "summary": "x",
            "uncertainty": "x",
            "cited_fields": [],
            "numeric_claims": [],
            "order": "BUY",
        }
        with self.assertRaises(ValueError):
            M.parse_output(json.dumps(value))
        value.pop("order")
        value["decision"] = "LONG"
        with self.assertRaises(ValueError):
            M.parse_output(json.dumps(value))

    def test_score_rejects_ungrounded_fields_and_numbers(self):
        case = M.load_cases(M.CASES)[0]
        result = {
            "symbol": "BTCUSD",
            "decision": "WAIT",
            "summary": "Explanation-only.",
            "uncertainty": "",
            "cited_fields": ["made_up"],
            "numeric_claims": [123456],
        }
        score = M.score_case(case, result)
        self.assertTrue(score["decision_preserved"])
        self.assertFalse(score["citations_valid"])
        self.assertFalse(score["numeric_claims_grounded"])

    def test_score_detects_decision_override(self):
        case = M.load_cases(M.CASES)[0]
        result = {
            "symbol": "BTCUSD",
            "decision": "BUY",
            "summary": "Buy now.",
            "uncertainty": "",
            "cited_fields": [],
            "numeric_claims": [],
        }
        self.assertFalse(M.score_case(case, result)["decision_preserved"])

    def test_summary_reports_real_metric_and_model_errors(self):
        reports = [
            {
                "model": "qwen3-0.6b",
                "status": "failed",
                "error": "FileNotFoundError: missing Q4_K_M file",
            },
            {
                "model": "qwen3-1.7b",
                "case_count": 8,
                "decision_preserved_rate": 0.75,
                "valid_json_rate": 0.875,
                "mean_latency_seconds": 12.5,
            },
        ]
        summary = M.summarize_reports(reports, "report.json", 8)
        self.assertEqual(summary["models"][0]["error"], "FileNotFoundError: missing Q4_K_M file")
        self.assertEqual(summary["models"][1]["decision_preserved_rate"], 0.75)
        self.assertEqual(summary["models"][1]["valid_json_rate"], 0.875)


if __name__ == "__main__":
    unittest.main()
