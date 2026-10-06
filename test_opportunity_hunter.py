import unittest
from opportunity_hunter import _score, _estimate_value, classify_source

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

    def test_source_classification(self):
        self.assertEqual(classify_source("https://www.toptal.com/talent/jobs", "Remote Freelance Web Developer Jobs", "", "clients")["kind"], "recruiter_platform")
        self.assertEqual(classify_source("https://www.fiverr.com/jobs", "Web developer project", "", "clients")["kind"], "marketplace")
        self.assertTrue(classify_source("https://example.com/project", "Need a website", "Looking for a web developer", "clients")["direct_client"])

if __name__ == "__main__":
    unittest.main()
