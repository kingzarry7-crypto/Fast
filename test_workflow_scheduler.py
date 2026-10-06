import unittest
from workflow_scheduler import status, run_once


class WorkflowSchedulerTests(unittest.TestCase):
    def test_status_is_observable(self):
        data = status()
        self.assertIn("running", data)
        self.assertIn("policy", data)
        self.assertIn("runs", data)

    def test_run_once_does_not_require_work(self):
        result = run_once(limit=1)
        self.assertIn("resumed", result)
        self.assertIn("errors", result)
        self.assertIn("checked", result)


if __name__ == "__main__":
    unittest.main()
