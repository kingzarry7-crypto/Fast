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

    def test_parse_discards_qwen_reasoning_and_keeps_final_json(self):
        case = M.load_cases(M.CASES)[0]
        result = {
            "symbol": case["symbol"],
            "decision": case["kitty"]["decision"],
            "summary": "Explanation-only: Kitty's WAIT is preserved because the supplied timeframe signals conflict.",
            "uncertainty": "The supplied entry confirmation remains unresolved.",
            "cited_fields": case["expected_fields"],
            "numeric_claims": [],
        }
        parsed = M.parse_output("<think>internal reasoning</think>\\n" + json.dumps(result))
        self.assertEqual(parsed, result)

    def test_parse_rejects_unterminated_thinking_block(self):
        with self.assertRaises(ValueError):
            M.parse_output("<think>unfinished reasoning")

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


    def test_score_rejects_generic_explanation(self):
        case = M.load_cases(M.CASES)[0]
        result = {
            "symbol": case["symbol"],
            "decision": case["kitty"]["decision"],
            "summary": "explanation-only",
            "uncertainty": "stale data",
            "cited_fields": case["expected_fields"],
            "numeric_claims": [],
        }
        self.assertFalse(M.score_case(case, result)["explanation_quality"])

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

    def test_score_rejects_ungrounded_numbers_in_explanation_text(self):
        case = M.load_cases(M.CASES)[0]
        result = {
            "symbol": "BTCUSD",
            "decision": "WAIT",
            "summary": "explanation-only: this is more than 50% certain.",
            "uncertainty": "",
            "cited_fields": case["expected_fields"],
            "numeric_claims": [],
        }
        score = M.score_case(case, result)
        self.assertIn("numeric_text_claims_grounded", score)
        self.assertFalse(score["numeric_text_claims_grounded"])

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

    def test_prompt_passes_expected_fields_and_kitty_decision_to_model(self):
        case = M.load_cases(M.CASES)[0]
        messages = M.build_messages(case)
        self.assertTrue(messages[1]["content"].startswith("/no_think\n"))
        user_payload = json.loads(messages[1]["content"].removeprefix("/no_think\n"))
        self.assertEqual(user_payload["expected_fields"], case["expected_fields"])
        self.assertEqual(user_payload["kitty_assessment"]["decision"], case["kitty"]["decision"])
        self.assertEqual(user_payload["task"], "Explain Kitty's assessment without changing it.")
        self.assertIn("if expected_fields is supplied", messages[0]["content"].lower())
        self.assertIn("include every listed key in cited_fields", messages[0]["content"].lower())
        self.assertIn("Never invent or estimate confidence percentages", messages[0]["content"])
        self.assertIn('exact literal phrase "explanation-only"', messages[0]["content"])
        self.assertIn("Do not include numeric digits or percentages in summary or uncertainty.", messages[0]["content"])
        self.assertIn("cited_fields must include every expected_fields key exactly as provided; do not omit any.", messages[0]["content"])
        self.assertIn("Write a concrete explanation of at least eight words", messages[0]["content"])
        self.assertIn("Uncertainty must contain at least four words", messages[0]["content"])
        self.assertIn("numeric_claims must be an empty array", messages[0]["content"])

    def test_benchmark_uses_the_exact_service_prompt_and_output_schema(self):
        self.assertEqual(M.SYSTEM, M.SYSTEM_PROMPT)
        self.assertEqual(M.OUTPUT_SCHEMA["properties"]["decision"]["enum"], ["BUY", "SELL", "WAIT", "NO TRADE"])

    def test_response_format_requires_every_expected_field(self):
        expected = ["trend_4h", "entry_5m", "last_price"]
        schema = M.response_format(expected)["schema"]["properties"]["cited_fields"]
        self.assertEqual(schema["items"]["enum"], expected)
        self.assertEqual(schema["minItems"], len(expected))
        self.assertEqual(schema["maxItems"], len(expected))

    def test_response_format_uses_strict_required_schema(self):
        response_format = M.response_format()
        self.assertEqual(response_format["type"], "json_object")
        schema = response_format["schema"]
        self.assertEqual(set(schema["required"]), M.REQUIRED)
        self.assertFalse(schema["additionalProperties"])
        self.assertEqual(schema["properties"]["summary"]["minLength"], 60)
        self.assertEqual(schema["properties"]["uncertainty"]["minLength"], 20)
        self.assertEqual(schema["properties"]["numeric_claims"]["maxItems"], 0)

    def test_summary_reports_real_metric_and_model_errors(self):
        reports = [
            {
                "model": "qwen3-0.6b",
                "status": "failed",
                "error": "FileNotFoundError: missing Q4_K_M file",
            },
            {
                "model": "smollm3-3b",
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
