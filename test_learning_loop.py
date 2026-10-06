import unittest
from learning_loop import extract_lessons


class LearningLoopTests(unittest.TestCase):
    def test_completed_workflow_creates_success_lesson(self):
        lessons = extract_lessons({
            "user_id": "u1",
            "goal": "find website clients",
            "status": "completed",
            "result": {"research": {"success": True}},
        })
        self.assertTrue(any(x["type"] == "workflow_success" for x in lessons))
        self.assertTrue(any(x["type"] == "research_pattern" for x in lessons))

    def test_failed_workflow_creates_failure_lesson(self):
        lessons = extract_lessons({
            "user_id": "u1",
            "goal": "deploy my app",
            "status": "failed",
            "plan": [{"status": "failed", "action": "external_action"}],
            "result": {},
        })
        self.assertEqual(lessons[0]["type"], "workflow_failure")


    def test_completed_external_workflow_without_verification_does_not_learn_success(self):
        lessons = extract_lessons({
            "user_id": "u1",
            "goal": "submit approved proposal",
            "status": "completed",
            "plan": [{"action": "browser_execute", "requires_approval": True, "status": "completed"}],
            "result": {},
        })
        self.assertFalse(any(x["type"] == "workflow_success" for x in lessons))

    def test_completed_external_workflow_with_verification_learns_success(self):
        lessons = extract_lessons({
            "user_id": "u1",
            "goal": "submit approved proposal",
            "status": "completed",
            "plan": [{"action": "browser_execute", "requires_approval": True, "status": "completed"}],
            "result": {
                "browser_execute": {
                    "verification": {
                        "verification_status": "verified_sent",
                        "verified": True,
                        "evidence": [{"type": "provider_confirmation", "text": "proposal submitted"}],
                    }
                }
            },
        })
        self.assertTrue(any(x["type"] == "workflow_success" for x in lessons))

    def test_empty_goal_does_not_learn(self):
        self.assertEqual(extract_lessons({"status": "completed"}), [])


if __name__ == "__main__":
    unittest.main()
