import unittest

import browser_operator


class BrowserOperatorTests(unittest.TestCase):
    def test_status_shape(self):
        result = browser_operator.status()
        self.assertIn("available", result)
        self.assertIn("policy", result)

    def test_external_action_requires_approval(self):
        with self.assertRaises(PermissionError):
            browser_operator.execute_plan("test-user", [{"type": "publish", "text": "Publish"}], allow_external=False)


if __name__ == "__main__":
    unittest.main()
