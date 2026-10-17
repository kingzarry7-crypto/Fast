import unittest
from unittest.mock import patch

from coding_request import handle_coding_request, is_coding_request


class CodingRequestTests(unittest.TestCase):
    def test_build_facebook_is_coding(self):
        self.assertTrue(is_coding_request("build Facebook"))

    def test_explicit_website_request_is_coding(self):
        self.assertTrue(is_coding_request("Create a responsive marketplace website"))

    def test_email_request_is_not_coding(self):
        self.assertFalse(is_coding_request("Draft an email to my client"))

    def test_general_question_is_not_coding(self):
        self.assertFalse(is_coding_request("What is Facebook?"))

    def test_coding_request_calls_executor_and_returns_project(self):
        project = {
            "success": True,
            "summary": "A responsive social network prototype",
            "files": [{"path": "index.html", "content": "<html></html>"}],
            "checks": [{"name": "HTML structure", "status": "passed"}],
            "file_count": 1,
        }
        with patch("engineering_executor.generate_project", return_value=project) as generate:
            result = handle_coding_request("build Facebook")
        generate.assert_called_once_with("build Facebook")
        self.assertEqual(result["provider"], "coding_agent")
        self.assertIn("index.html", result["reply"])
        self.assertIn("```html", result["reply"])
        self.assertIn("<html></html>", result["reply"])
        self.assertEqual(result["project"], project)

    def test_generation_error_is_explicit_and_does_not_claim_success(self):
        with patch("engineering_executor.generate_project", side_effect=RuntimeError("provider down")):
            result = handle_coding_request("build Facebook")
        self.assertEqual(result["status"], "error")
        self.assertIsNone(result["project"])
        self.assertIn("failed", result["reply"].lower())


if __name__ == "__main__":
    unittest.main()
