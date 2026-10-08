"""Tests for the KZ Agent orchestration layer."""
import unittest

import kz_agent


class KZAgentSnapshotTests(unittest.TestCase):
    def test_snapshot_reports_current_approval(self):
        item = {
            "id": "abc",
            "goal": "send an approved message",
            "status": "waiting_for_approval",
            "risk": "yellow",
            "requires_approval": True,
            "plan": [
                {"id": "s1", "title": "Research", "action": "research_goal", "status": "completed", "risk": "green"},
                {"id": "s2", "title": "Send", "action": "external_action", "status": "waiting_for_approval", "risk": "yellow", "requires_approval": True, "approval_id": "ap-1"},
            ],
            "result": {},
            "potential_revenue": 0,
            "updated_at": "now",
        }
        result = kz_agent.snapshot(item)
        self.assertEqual(result["status"], "waiting_for_approval")
        self.assertEqual(result["current_step"]["approval_id"], "ap-1")
        self.assertEqual(result["completed_steps"], 1)
        self.assertEqual(result["total_steps"], 2)


if __name__ == "__main__":
    unittest.main()
