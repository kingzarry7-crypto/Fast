import importlib.util, json, unittest
from pathlib import Path
SCRIPT=Path(__file__).resolve().parents[1]/"research-data/scripts/zarry_model_benchmark.py"
SPEC=importlib.util.spec_from_file_location("zarry_model_benchmark",SCRIPT)
M=importlib.util.module_from_spec(SPEC); SPEC.loader.exec_module(M)

class BenchmarkContractTests(unittest.TestCase):
 def test_cases_cover_both_assets_and_all_decisions(self):
  cases=M.load_cases(M.CASES)
  self.assertEqual(len(cases),8)
  self.assertEqual({x["symbol"] for x in cases},{"BTCUSD","XAUUSD"})
  self.assertEqual({x["kitty"]["decision"] for x in cases},{"BUY","SELL","WAIT"})
 def test_parse_accepts_exact_schema(self):
  value={"symbol":"BTCUSD","decision":"WAIT","summary":"Explanation-only.","uncertainty":"Conflict.","cited_fields":["trend_4h"],"numeric_claims":[]}
  self.assertEqual(M.parse_output(json.dumps(value)),value)
 def test_parse_rejects_extra_keys_and_invalid_decisions(self):
  value={"symbol":"BTCUSD","decision":"WAIT","summary":"x","uncertainty":"x","cited_fields":[],"numeric_claims":[],"order":"BUY"}
  with self.assertRaises(ValueError): M.parse_output(json.dumps(value))
  value.pop("order"); value["decision"]="LONG"
  with self.assertRaises(ValueError): M.parse_output(json.dumps(value))
 def test_score_rejects_ungrounded_fields_and_numbers(self):
  case=M.load_cases(M.CASES)[0]
  result={"symbol":"BTCUSD","decision":"WAIT","summary":"Explanation-only.","uncertainty":"","cited_fields":["made_up"],"numeric_claims":[123456]}
  score=M.score_case(case,result)
  self.assertTrue(score["decision_preserved"]); self.assertFalse(score["citations_valid"]); self.assertFalse(score["numeric_claims_grounded"])
 def test_score_detects_decision_override(self):
  case=M.load_cases(M.CASES)[0]
  result={"symbol":"BTCUSD","decision":"BUY","summary":"Buy now.","uncertainty":"","cited_fields":[],"numeric_claims":[]}
  self.assertFalse(M.score_case(case,result)["decision_preserved"])

if __name__=="__main__": unittest.main()
