import unittest
from delivery_agent import build_package, verify


class DeliveryAgentTests(unittest.TestCase):
    def workflow(self, status="completed"):
        return {
            "id": "wf-123",
            "user_id": "u-1",
            "goal": "Build a five-page business website",
            "status": status,
            "result": {"verified": True, "completed_at": "2026-10-06T00:00:00Z"},
        }

    def test_completed_work_creates_approval_gated_package(self):
        package = build_package(self.workflow())
        self.assertEqual(package["status"], "ready_for_approval")
        self.assertTrue(package["approval_required"])
        self.assertEqual(package["handoff"]["send_status"], "draft_only")

    def test_incomplete_work_cannot_be_delivered(self):
        package = build_package(self.workflow("executing"))
        self.assertEqual(package["status"], "blocked_pending_verification")

    def test_qa_requires_both_checks(self):
        package = build_package(self.workflow())
        checked = verify(package, {"deliverables_reviewed": True, "result_checked": True})
        self.assertEqual(checked["status"], "verified_ready_for_approval")
        self.assertTrue(checked["verification"]["qa_passed"])

        blocked = verify(package, {"deliverables_reviewed": True})
        self.assertEqual(blocked["status"], "blocked_pending_qa")


if __name__ == "__main__":
    unittest.main()
