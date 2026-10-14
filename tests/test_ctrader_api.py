import unittest
import time
from ctrader_api import _sign_state, _verify_state


class CTraderStateTests(unittest.TestCase):
    def test_signed_state_round_trip(self):
        state = _sign_state("user-123", "a-long-test-secret-at-least-32-characters")
        self.assertEqual(_verify_state(state, "a-long-test-secret-at-least-32-characters"), "user-123")

    def test_tampered_state_rejected(self):
        secret = "a-long-test-secret-at-least-32-characters"
        state = _sign_state("user-123", secret)
        self.assertNotEqual(state, state + "x")
        with self.assertRaises(Exception):
            _verify_state(state + "x", secret)


if __name__ == "__main__":
    unittest.main()
