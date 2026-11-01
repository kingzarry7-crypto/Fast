import unittest
from unittest.mock import Mock

import web_settings_patch


class WebSettingsPlatformIdentityTests(unittest.TestCase):
    def test_read_skips_database_for_telegram_service_identity(self):
        cursor_factory = Mock()
        result = web_settings_patch._read_settings("telegram:market_engine_mtf", cursor_factory)
        self.assertEqual(result, web_settings_patch.DEFAULTS)
        cursor_factory.assert_not_called()

    def test_read_skips_database_for_discord_identity(self):
        cursor_factory = Mock()
        result = web_settings_patch._read_settings("discord:123456", cursor_factory)
        self.assertEqual(result, web_settings_patch.DEFAULTS)
        cursor_factory.assert_not_called()

    def test_write_rejects_non_web_identity_before_database_access(self):
        cursor_factory = Mock()
        with self.assertRaisesRegex(ValueError, "web-user UUID"):
            web_settings_patch._write_settings(
                "telegram:market_engine_mtf",
                dict(web_settings_patch.DEFAULTS),
                cursor_factory,
            )
        cursor_factory.assert_not_called()

    def test_read_allows_valid_web_uuid(self):
        cursor = Mock()
        cursor.__enter__ = Mock(return_value=cursor)
        cursor.__exit__ = Mock(return_value=False)
        cursor.fetchone.return_value = None
        cursor_factory = Mock(return_value=cursor)
        result = web_settings_patch._read_settings(
            "8b8b6f4e-9c6a-4b7e-9d6d-3e4cdbf6c1a1",
            cursor_factory,
        )
        self.assertEqual(result, web_settings_patch.DEFAULTS)
        cursor_factory.assert_called_once_with(commit=False)


if __name__ == "__main__":
    unittest.main()
