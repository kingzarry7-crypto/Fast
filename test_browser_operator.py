import unittest

import browser_operator


class BrowserOperatorTests(unittest.TestCase):
    def test_status_shape(self):
        result = browser_operator.status()
        self.assertIn("available", result)
        self.assertIn("policy", result)


    def test_verification_requires_destination_evidence(self):
        before = {"url": "https://example.test/form", "title": "Form", "text": "Form"}
        after = {"url": "https://example.test/done", "title": "Done", "text": "Application submitted successfully"}
        result = browser_operator._verification_evidence(
            before,
            after,
            [{"type": "submit", "text": "Submit"}],
        )
        self.assertEqual(result["verification_status"], "verified_sent")
        self.assertTrue(result["verified"])

    def test_verification_does_not_assume_success_from_url_change(self):
        before = {"url": "https://example.test/form", "title": "Form", "text": "Form"}
        after = {"url": "https://example.test/done", "title": "Done", "text": "Thanks"}
        result = browser_operator._verification_evidence(
            before,
            after,
            [{"type": "submit", "text": "Submit"}],
        )
        self.assertEqual(result["verification_status"], "not_verified")
        self.assertFalse(result["verified"])

    def test_external_action_requires_approval(self):
        with self.assertRaises(PermissionError):
            browser_operator.execute_plan("test-user", [{"type": "publish", "text": "Publish"}], allow_external=False)


if __name__ == "__main__":
    unittest.main()
