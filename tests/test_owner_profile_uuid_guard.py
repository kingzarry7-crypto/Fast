import unittest
from unittest.mock import patch

import owner_profile


class OwnerProfileUUIDGuardTests(unittest.TestCase):
    def test_non_uuid_service_id_skips_web_database_read(self):
        with patch("database.get_db_cursor") as cursor:
            self.assertEqual(owner_profile._db_get("market_engine_mtf"), {})
        cursor.assert_not_called()

    def test_platform_id_skips_web_database_read(self):
        with patch("database.get_db_cursor") as cursor:
            self.assertEqual(owner_profile._db_get("telegram:123456"), {})
        cursor.assert_not_called()

    def test_non_uuid_profile_is_kept_in_memory_without_database_write(self):
        with patch("database.get_db_cursor") as cursor:
            result = owner_profile.save_profile(
                "market_engine_mtf",
                {
                    "display_name": "Market Engine",
                    "professional_title": "Internal service",
                },
            )
        cursor.assert_not_called()
        self.assertEqual(result["display_name"], "Market Engine")


if __name__ == "__main__":
    unittest.main()
