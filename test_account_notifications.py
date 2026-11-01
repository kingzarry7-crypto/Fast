import unittest
from unittest.mock import patch

from account_notifications import (
    mark_account_notification_delivered,
    pending_account_notifications,
    queue_account_notification,
    users_with_pending_account_notifications,
)


class AccountNotificationChannelTests(unittest.TestCase):
    def test_platform_identity_is_not_persisted_in_uuid_scoped_notifications(self):
        with patch("account_notifications._ensure_table") as ensure:
            result = queue_account_notification(
                "telegram:market_engine_mtf", "google", "account_monitor", {}
            )
        self.assertIsNone(result)
        ensure.assert_not_called()

    def test_platform_identity_is_not_used_for_uuid_scoped_notification_reads(self):
        with patch("account_notifications._ensure_table") as ensure:
            self.assertEqual(
                pending_account_notifications("telegram:market_engine_mtf", "telegram"), []
            )
        ensure.assert_not_called()

    def test_unknown_delivery_channel_is_rejected(self):
        with patch("account_notifications._ensure_table") as ensure:
            self.assertEqual(pending_account_notifications("user-1", "email"), [])
            self.assertFalse(mark_account_notification_delivered("notification-1", "email"))
            self.assertEqual(users_with_pending_account_notifications("email"), [])
            ensure.assert_not_called()


if __name__ == "__main__":
    unittest.main()
