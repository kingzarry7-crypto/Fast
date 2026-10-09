import os
import unittest
from pathlib import Path

import browser_operator


class BrowserOperatorTests(unittest.TestCase):
    def test_status_shape(self):
        result = browser_operator.status()
        self.assertIn("available", result)
        self.assertIn("policy", result)


    def test_connection_status_detects_login_required(self):
        class Body:
            def inner_text(self, timeout=0):
                return "Please sign in to continue"
        class Passwords:
            def count(self):
                return 1
        class FakePage:
            url = "https://example.test/login"
            def title(self):
                return "Example Login"
            def locator(self, selector):
                if selector == 'input[type="password"]':
                    return Passwords()
                return Body()
        original_page = browser_operator._page
        original_detect = browser_operator._set_human_verification_state
        try:
            browser_operator._page = lambda user_id, account_id=None: FakePage()
            browser_operator._set_human_verification_state = lambda user_id, page, account_id=None: {"required": False}
            state = browser_operator.connection_status("test-user")
            self.assertEqual(state["status"], "login_required")
            self.assertFalse(state["connected"])
        finally:
            browser_operator._page = original_page
            browser_operator._set_human_verification_state = original_detect

    def test_connection_status_does_not_assume_login_from_neutral_page(self):
        class Body:
            def inner_text(self, timeout=0):
                return "Welcome to Example Marketplace"
        class Passwords:
            def count(self):
                return 0
        class FakePage:
            url = "https://example.test/"
            def title(self):
                return "Example Marketplace"
            def locator(self, selector):
                if selector == 'input[type="password"]':
                    return Passwords()
                return Body()
        original_page = browser_operator._page
        original_detect = browser_operator._set_human_verification_state
        try:
            browser_operator._page = lambda user_id, account_id=None: FakePage()
            browser_operator._set_human_verification_state = lambda user_id, page, account_id=None: {"required": False}
            state = browser_operator.connection_status("test-user")
            self.assertEqual(state["status"], "login_required")
            self.assertTrue(state["login_required"])
            self.assertFalse(state["connected"])
        finally:
            browser_operator._page = original_page
            browser_operator._set_human_verification_state = original_detect

    def test_connection_status_accepts_strong_authenticated_page_evidence(self):
        class Body:
            def inner_text(self, timeout=0):
                return "Dashboard Account Settings Log out"
        class Passwords:
            def count(self):
                return 0
        class FakePage:
            url = "https://example.test/dashboard"
            def title(self):
                return "Dashboard"
            def locator(self, selector):
                if selector == 'input[type="password"]':
                    return Passwords()
                return Body()
        original_page = browser_operator._page
        original_detect = browser_operator._set_human_verification_state
        original_sessions = browser_operator._SESSIONS
        try:
            browser_operator._page = lambda user_id, account_id=None: FakePage()
            browser_operator._set_human_verification_state = lambda user_id, page, account_id=None: {"required": False}
            browser_operator._SESSIONS = {"test-user::default": {}}
            state = browser_operator.connection_status("test-user")
            self.assertEqual(state["status"], "ready_to_confirm")
            self.assertFalse(state["connected"])
            self.assertFalse(state["login_required"])
            self.assertTrue(state["login_evidence"]["positive_auth_signal"])
        finally:
            browser_operator._page = original_page
            browser_operator._set_human_verification_state = original_detect
            browser_operator._SESSIONS = original_sessions

    def test_connection_status_detects_fiverr_authenticated_shell_without_logout_text(self):
        class Body:
            def inner_text(self, timeout=0):
                return "Switch to Selling Inbox My Gigs"
        class Passwords:
            def count(self):
                return 0
        class Links:
            def count(self):
                return 1
        class FakePage:
            url = "https://www.fiverr.com/users/test"
            def title(self):
                return "Fiverr"
            def locator(self, selector):
                if selector == 'input[type="password"]':
                    return Passwords()
                if 'a[href*="/users/"]' in selector:
                    return Links()
                return Body()
        original_page = browser_operator._page
        original_detect = browser_operator._set_human_verification_state
        original_sessions = browser_operator._SESSIONS
        try:
            browser_operator._SESSIONS = {"test-user::default": {}}
            browser_operator._page = lambda user_id, account_id=None: FakePage()
            browser_operator._set_human_verification_state = lambda user_id, page, account_id=None: {"required": False}
            state = browser_operator.connection_status("test-user")
            self.assertEqual(state["status"], "ready_to_confirm")
            self.assertTrue(state["authenticated"])
            self.assertIn("switch to selling", state["login_evidence"]["provider_markers"])
        finally:
            browser_operator._page = original_page
            browser_operator._set_human_verification_state = original_detect
            browser_operator._SESSIONS = original_sessions

    def test_connection_status_allows_explicit_confirmation_state(self):
        class Body:
            def inner_text(self, timeout=0):
                return "Dashboard"
        class Passwords:
            def count(self):
                return 0
        class FakePage:
            url = "https://example.test/dashboard"
            def title(self):
                return "Dashboard"
            def locator(self, selector):
                if selector == 'input[type="password"]':
                    return Passwords()
                return Body()
        original_page = browser_operator._page
        original_detect = browser_operator._set_human_verification_state
        original_sessions = browser_operator._SESSIONS
        try:
            browser_operator._SESSIONS = {"test-user::default": {"account_connected": True}}
            browser_operator._page = lambda user_id, account_id=None: FakePage()
            browser_operator._set_human_verification_state = lambda user_id, page, account_id=None: {"required": False}
            state = browser_operator.connection_status("test-user")
            self.assertEqual(state["status"], "unknown")
            self.assertFalse(state["connected"])
            self.assertTrue(browser_operator._SESSIONS["test-user::default"]["account_connected"])
        finally:
            browser_operator._page = original_page
            browser_operator._set_human_verification_state = original_detect
            browser_operator._SESSIONS = original_sessions

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



    def test_human_verification_detector_flags_fiverr_challenge(self):
        class Body:
            def inner_text(self, timeout=0):
                return "It needs a human touch Loading challenge"
        class FakePage:
            url = "https://www.fiverr.com/"
            def title(self):
                return "Fiverr"
            def locator(self, selector):
                return Body()
        result = browser_operator._detect_human_verification(FakePage())
        self.assertTrue(result["required"])
        self.assertIn("loading challenge", result["indicators"])
        self.assertIn("it needs a human touch", result["indicators"])

    def test_human_verification_detector_allows_normal_page(self):
        class Body:
            def inner_text(self, timeout=0):
                return "Fiverr login page"
        class FakePage:
            url = "https://www.fiverr.com/login"
            def title(self):
                return "Fiverr Login"
            def locator(self, selector):
                return Body()
        result = browser_operator._detect_human_verification(FakePage())
        self.assertFalse(result["required"])

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


    def test_connection_status_never_keeps_connected_after_auth_evidence_disappears(self):
        class Body:
            def inner_text(self, timeout=0):
                return "Welcome back"
        class Passwords:
            def count(self):
                return 0
        class FakePage:
            url = "https://example.test/"
            def title(self):
                return "Example"
            def locator(self, selector):
                if selector == 'input[type="password"]':
                    return Passwords()
                return Body()
        original_page = browser_operator._page
        original_detect = browser_operator._set_human_verification_state
        original_sessions = browser_operator._SESSIONS
        try:
            browser_operator._SESSIONS = {"test-user::default": {"account_connected": True}}
            browser_operator._page = lambda user_id, account_id=None: FakePage()
            browser_operator._set_human_verification_state = lambda user_id, page, account_id=None: {"required": False}
            state = browser_operator.connection_status("test-user")
            self.assertEqual(state["status"], "unknown")
            self.assertFalse(state["connected"])
            self.assertTrue(browser_operator._SESSIONS["test-user::default"]["account_connected"])
        finally:
            browser_operator._page = original_page
            browser_operator._set_human_verification_state = original_detect
            browser_operator._SESSIONS = original_sessions


if __name__ == "__main__":
    unittest.main()
