import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from smoke_test import is_allowed_base_url


class SmokeTestTargetTests(unittest.TestCase):
    def test_allows_https_service_url(self):
        self.assertTrue(is_allowed_base_url("https://zarry-production.up.railway.app"))

    def test_allows_http_loopback_for_internal_startup_smoke(self):
        self.assertTrue(is_allowed_base_url("http://127.0.0.1:8080"))
        self.assertTrue(is_allowed_base_url("http://localhost:8080"))

    def test_rejects_external_http(self):
        self.assertFalse(is_allowed_base_url("http://zarry-production.up.railway.app"))

    def test_rejects_non_http_schemes_and_invalid_urls(self):
        self.assertFalse(is_allowed_base_url("ftp://example.com"))
        self.assertFalse(is_allowed_base_url("not-a-url"))


if __name__ == "__main__":
    unittest.main()
