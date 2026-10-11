import unittest
from unittest.mock import patch

from account_notifications import (
    mark_account_notification_delivered,
    pending_account_notifications,
    users_with_pending_account_notifications,
)


class AccountNotificationChannelTests(unittest.TestCase):
    def test_unknown_delivery_channel_is_rejected(self):
        with patch("account_notifications._ensure_table") as ensure:
            self.assertEqual(pending_account_notifications("user-1", "email"), [])
            self.assertFalse(mark_account_notification_delivered("notification-1", "email"))
            self.assertEqual(users_with_pending_account_notifications("email"), [])
            ensure.assert_not_called()


if __name__ == "__main__":
    unittest.main()
