"""Tests for the centralized Action Gateway risk policy."""
import unittest

from action_risk_policy import (
    RISK_GREEN,
    RISK_YELLOW,
    RISK_RED,
    risk_for_action,
    requires_approval,
    validate_payload,
)


class ActionRiskPolicyTests(unittest.TestCase):
    def test_risk_classes_are_centralized(self):
        self.assertEqual(risk_for_action("account.read"), RISK_GREEN)
        self.assertEqual(risk_for_action("whatsapp.send"), RISK_YELLOW)
        self.assertEqual(risk_for_action("trade.close_position"), RISK_RED)
        self.assertEqual(risk_for_action("trade.place_order"), RISK_RED)

    def test_consequential_actions_require_approval(self):
        self.assertFalse(requires_approval("account.read"))
        self.assertTrue(requires_approval("whatsapp.send"))
        self.assertTrue(requires_approval("trade.place_order"))

    def test_trade_quantity_is_positive_and_finite(self):
        data = validate_payload("trade.place_order", {"symbol": "BTC/USD", "side": "BUY", "quantity": 0.01})
        self.assertEqual(data["_risk_level"], RISK_RED)
        with self.assertRaises(ValueError):
            validate_payload("trade.place_order", {"quantity": 0})
        with self.assertRaises(ValueError):
            validate_payload("trade.place_order", {"quantity": "nan"})

    def test_whatsapp_shape_is_validated(self):
        data = validate_payload("whatsapp.send", {"to": "+2348012345678", "text": "Hello"})
        self.assertEqual(data["_risk_level"], RISK_YELLOW)
        with self.assertRaises(ValueError):
            validate_payload("whatsapp.send", {"to": "+2348012345678", "text": ""})


if __name__ == "__main__":
    unittest.main()
