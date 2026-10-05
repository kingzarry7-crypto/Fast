import unittest
from client_acquisition import qualify, draft_outreach

class ClientAcquisitionTests(unittest.TestCase):
    def test_qualifies_web_project(self):
        r = qualify({"title":"Need a web developer","summary":"Paid website redesign project","url":"https://example.com"})
        self.assertGreaterEqual(r["fit_score"], 90)
        self.assertTrue(r["needs_manual_verification"])

    def test_draft_never_authorizes_send(self):
        r = draft_outreach({"title":"Landing page project","summary":"Looking for a developer"}, {"reasons":["fit"]})
        self.assertEqual(r["send_status"], "draft_only")
        self.assertTrue(r["approval_required"])

if __name__ == "__main__":
    unittest.main()
