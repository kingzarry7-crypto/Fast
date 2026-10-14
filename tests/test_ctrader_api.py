import unittest
from ctrader_api import _sign_state, _verify_state
import time


class CTraderStateTests(unittest.TestCase):
    def test_signed_state_round_trip(self):
        secret = "test-secret"
        state = _sign_state(f"user-123:{int(time.time())}", secret)
        self.assertTrue(_verify_state(state, secret))

    def test_tampered_state_rejected(self):
        secret = "test-secret"
        state = _sign_state(f"user-123:{int(time.time())}", secret)
        self.assertFalse(_verify_state(state + "x", secret))

    def test_expired_state_rejected(self):
        state = _sign_state(f"user-123:{int(time.time()) - 9999}", "test-secret")
        self.assertFalse(_verify_state(state, "test-secret"))


if __name__ == "__main__":
    unittest.main()
