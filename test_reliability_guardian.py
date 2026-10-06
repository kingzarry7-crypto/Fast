import unittest
from reliability_guardian import record_failure, snapshot, stale_workflow_action


class ReliabilityGuardianTests(unittest.TestCase):
    def test_green_failure_is_retryable(self):
        result = record_failure(RuntimeError("temporary"), risk="green", attempts=1)
        self.assertEqual(result["decision"], "retry")

    def test_red_failure_is_surfaced(self):
        result = record_failure(RuntimeError("external"), risk="red", attempts=1)
        self.assertEqual(result["decision"], "surface")

    def test_approval_is_never_auto_approved(self):
        self.assertEqual(stale_workflow_action("waiting_for_approval", 120), "notify_approval")

    def test_snapshot_has_policy(self):
        self.assertIn("policy", snapshot())


if __name__ == "__main__":
    unittest.main()
