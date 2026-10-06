import unittest

import job_outreach_agent


class JobOutreachAgentTests(unittest.TestCase):
    def test_report_does_not_call_estimates_confirmed_revenue(self):
        report = job_outreach_agent._report([
            {"id": "1", "title": "Website", "url": "https://example.com",
             "score": 80, "confidence": "high", "estimated_value": 350,
             "source_kind": "direct_client", "next_action": "prepare"},
        ])
        self.assertEqual(report["estimated_value"], 350)
        self.assertIn("not guaranteed", report["warning"].lower())

    def test_execution_status_requires_evidence(self):
        workflow = {
            "status": "completed",
            "result": {
                "browser_execute": {
                    "verification": {
                        "verification_status": "not_verified",
                        "verified": False,
                    }
                }
            },
        }
        self.assertEqual(
            job_outreach_agent._execution_status(workflow),
            "sent_not_verified",
        )


if __name__ == "__main__":
    unittest.main()
