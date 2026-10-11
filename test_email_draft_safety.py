import unittest

from email_draft_safety import is_email_draft_followup


class EmailDraftSafetyTests(unittest.TestCase):
    def setUp(self):
        self.history = [
            {"role": "assistant", "content": "Here is the email draft: To: kingzaza700@gmail.com Subject: Message from King Zarry AI"},
            {"role": "assistant", "content": "Key Update Details: Improved conversation flow and response accuracy"},
        ]

    def test_revision_request_stays_in_email_draft_mode(self):
        self.assertTrue(is_email_draft_followup("Add specific update details", self.history))

    def test_send_it_stays_bound_to_existing_email_draft(self):
        self.assertTrue(is_email_draft_followup("Send it", self.history))

    def test_source_link_followup_does_not_lose_email_context(self):
        self.assertTrue(is_email_draft_followup("Request a verified source link", self.history))

    def test_unrelated_new_question_is_not_email_draft_mode(self):
        self.assertFalse(is_email_draft_followup("What is the weather today?", self.history))

    def test_email_mention_without_an_active_draft_is_not_enough(self):
        history = [{"role": "user", "content": "I use email at work."}]
        self.assertFalse(is_email_draft_followup("Add specific update details", history))


if __name__ == "__main__":
    unittest.main()
