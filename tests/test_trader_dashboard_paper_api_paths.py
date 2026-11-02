"""Regression tests for the Trader dashboard's canonical Kitty paper API paths."""
from pathlib import Path
import unittest


class TraderDashboardPaperApiPathTests(unittest.TestCase):
    def test_dashboard_uses_registered_kitty_multi_paper_endpoints(self):
        source = (
            Path(__file__).resolve().parents[1]
            .joinpath("frontend", "app", "trader", "page.tsx")
            .read_text(encoding="utf-8")
        )
        self.assertIn(
            'fetch("/api/kitty/multi-paper/status"',
            source,
            "Trader paper status must call the registered /api/kitty/multi-paper/status route",
        )
        self.assertIn(
            'fetch("/api/kitty/multi-paper/signals?',
            source,
            "Trader paper signals must call the registered /api/kitty/multi-paper/signals route",
        )
        self.assertNotIn('fetch("/api/trader/paper/status"', source)
        self.assertNotIn('fetch("/api/trader/paper/signals?', source)


if __name__ == "__main__":
    unittest.main()
