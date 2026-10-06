import os
import unittest
from pathlib import Path

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



    def test_verification_does_not_treat_filled_text_as_submission_proof(self):
        before = {"url": "https://example.test/form", "title": "Form", "text": "Form"}
        after = {"url": "https://example.test/form", "title": "Form", "text": "Form\nMy proposal text"}
        result = browser_operator._verification_evidence(
            before,
            after,
            [{"type": "fill", "selector": "#message", "value": "My proposal text"},
             {"type": "submit", "text": "Submit"}],
        )
        self.assertEqual(result["verification_status"], "not_verified")
        self.assertFalse(result["verified"])
        self.assertEqual(result["method"], "none")

    def test_real_chromium_safe_smoke_when_available(self):
        """Exercise real Playwright Chromium without touching an external site."""
        if browser_operator.sync_playwright is None:
            self.skipTest("Playwright is not installed")
        executable = os.getenv("BROWSER_EXECUTABLE_PATH") or "/usr/bin/chromium"
        if not Path(executable).exists():
            try:
                with browser_operator.sync_playwright() as p:
                    executable = p.chromium.executable_path
            except Exception:
                self.skipTest("No Chromium executable available")
        if not Path(executable).exists():
            self.skipTest("Chromium executable is unavailable")
        original = os.environ.get("BROWSER_EXECUTABLE_PATH")
        os.environ["BROWSER_EXECUTABLE_PATH"] = str(executable)
        user_id = "browser-smoke-test"
        try:
            page = browser_operator.navigate(user_id, "data:text/html,<html><head><title>KZ Browser Smoke</title></head><body><h1>Browser runtime OK</h1><p>safe local test</p></body></html>")
            self.assertEqual(page["title"], "KZ Browser Smoke")
            inspected = browser_operator.inspect(user_id)
            self.assertIn("Browser runtime OK", inspected["text"])
        finally:
            browser_operator.close(user_id)
            if original is None:
                os.environ.pop("BROWSER_EXECUTABLE_PATH", None)
            else:
                os.environ["BROWSER_EXECUTABLE_PATH"] = original

    def test_marketplace_send_click_requires_approval(self):
        with self.assertRaises(PermissionError):
            browser_operator.execute_plan(
                "test-user",
                [{"type": "click", "text": "Send proposal"}],
                allow_external=False,
            )

    def test_external_action_requires_approval(self):
        with self.assertRaises(PermissionError):
            browser_operator.execute_plan("test-user", [{"type": "publish", "text": "Publish"}], allow_external=False)


if __name__ == "__main__":
    unittest.main()
