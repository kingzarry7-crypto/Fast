import unittest
from opportunity_hunter import _score, _estimate_value

class OpportunityHunterTests(unittest.TestCase):
    def test_strong_client_signal(self):
        item = {"title":"Need a web developer for website redesign","content":"Looking for a developer. Paid project, urgent.","url":"https://example.com/job"}
        scored = _score(item, "clients")
        self.assertGreaterEqual(scored["score"], 70)
        self.assertEqual(scored["confidence"], "high")

    def test_value_bands(self):
        self.assertEqual(_estimate_value("clients", 40), 80.0)
        self.assertEqual(_estimate_value("clients", 70), 180.0)
        self.assertEqual(_estimate_value("clients", 90), 350.0)

if __name__ == "__main__":
    unittest.main()
