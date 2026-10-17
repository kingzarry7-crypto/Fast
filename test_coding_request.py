import unittest
from unittest.mock import patch

from coding_request import _build_html_preview, _format_project, handle_coding_request, is_coding_request


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


    def test_html_preview_bundles_local_css_and_javascript(self):
        preview = _build_html_preview([
            {"path": "index.html", "content": '<html><head><link rel="stylesheet" href="styles.css"></head><body><h1>Pagetsx</h1><script src="script.js"></script></body></html>'},
            {"path": "styles.css", "content": "body { color: red; }"},
            {"path": "script.js", "content": 'console.log("preview works");'},
        ])
        self.assertIn("<style>\nbody { color: red; }\n</style>", preview)
        self.assertIn('<script>\nconsole.log("preview works");\n</script>', preview)
        self.assertNotIn('href="styles.css"', preview)
        self.assertNotIn('src="script.js"', preview)

    def test_project_reply_includes_bundled_preview_and_larger_code_budget(self):
        project = {
            "summary": "Pagetsx",
            "files": [
                {"path": "index.html", "content": '<html><head><link rel="stylesheet" href="styles.css"></head><body>Pagetsx</body></html>'},
                {"path": "styles.css", "content": "body { color: red; }"},
            ],
            "checks": [],
        }
        reply = _format_project(project)
        self.assertIn("html-preview", reply)
        self.assertIn("body { color: red; }", reply)
        self.assertIn("Project source files", reply)

    def test_generation_error_is_explicit_and_does_not_claim_success(self):
        with patch("engineering_executor.generate_project", side_effect=RuntimeError("provider down")):
            result = handle_coding_request("build Facebook")
        self.assertEqual(result["status"], "error")
        self.assertIsNone(result["project"])
        self.assertIn("failed", result["reply"].lower())


if __name__ == "__main__":
    unittest.main()
