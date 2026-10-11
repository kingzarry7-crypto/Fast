import unittest

from gmail_intelligence import classify_email, enrich_email, format_email_alert, format_email_digest, summarize_email


class GmailIntelligenceTests(unittest.TestCase):
    def test_security_warning_is_high(self):
        result = classify_email({"subject": "Security alert: suspicious sign-in"})
        self.assertEqual(result["priority"], "high")
        self.assertTrue(result["reason"])

    def test_deadline_is_high(self):
        self.assertEqual(classify_email({"subject": "Deadline today"})["priority"], "high")

    def test_reply_request_is_medium(self):
        self.assertEqual(classify_email({"subject": "Please reply with your availability"})["priority"], "medium")

    def test_newsletter_is_low(self):
        self.assertEqual(classify_email({"from": "weekly-newsletter@example.com", "subject": "Weekly digest"})["priority"], "low")

    def test_security_overrides_automated_sender(self):
        self.assertEqual(classify_email({"from": "no-reply@example.com", "subject": "Action required: verify your account"})["priority"], "high")

    def test_summary_uses_only_provider_preview(self):
        self.assertEqual(summarize_email({"snippet": "  Your appointment is tomorrow.  "}), "Your appointment is tomorrow.")
        self.assertIn("did not provide a preview", summarize_email({}))

    def test_alert_contains_explanation_and_next_step(self):
        alert = format_email_alert(enrich_email({"from": "person@example.com", "subject": "Meeting", "snippet": "Can we meet?"}))
        for part in ("person@example.com", "Meeting", "Why:", "Summary:", "Suggested next step:"):
            self.assertIn(part, alert)

    def test_digest_is_bounded(self):
        digest = format_email_digest([{"subject": f"News {i}", "from": "digest@example.com"} for i in range(8)])
        self.assertIn("8 email(s)", digest)
        self.assertIn("Plus 3 more", digest)


if __name__ == "__main__":
    unittest.main()
