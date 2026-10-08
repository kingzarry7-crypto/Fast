import unittest
from unittest.mock import patch

import kz_watcher


class KZWatcherTests(unittest.TestCase):
    def test_scan_is_read_only_and_ranks_findings(self):
        rows = [
            {
                "id": "abc",
                "category": "clients",
                "title": "Business needs a web developer",
                "url": "https://example.com/project",
                "summary": "Looking for a paid website project.",
                "score": 80,
                "confidence": "high",
                "estimated_value": 350,
                "source_kind": "direct_client",
                "suggested_action": "Verify the project before preparing outreach.",
            }
        ]
        with patch.object(kz_watcher, "_conn", return_value=None),              patch("opportunity_hunter.hunt", return_value={"opportunities": rows}):
            result = kz_watcher.scan_user("test-user", categories=["clients"])
        self.assertEqual(result["status"], "completed")
        self.assertEqual(result["found_count"], 1)
        self.assertEqual(result["findings"][0]["score"], 80)
        self.assertEqual(result["findings"][0]["status"], "new")

    def test_empty_user_is_rejected(self):
        with self.assertRaises(ValueError):
            kz_watcher.scan_user("")


if __name__ == "__main__":
    unittest.main()
