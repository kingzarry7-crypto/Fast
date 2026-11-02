import unittest

from kitty_gold_model import evaluate_signal_gate


class KittyGoldSignalGateTests(unittest.TestCase):
    def test_unvalidated_edge_blocks_directional_signal_with_specific_reason(self):
        result = evaluate_signal_gate(
            best_class="LONG", confidence=0.91, margin=0.30,
            edge_validated=False, minimum_confidence=0.70,
        )
        self.assertEqual(result["signal"], "NO TRADE")
        self.assertEqual(result["candidate_signal"], "LONG")
        self.assertEqual(result["signal_gate"], "holdout_edge_not_validated")

    def test_neutral_class_is_reported_without_directional_signal(self):
        result = evaluate_signal_gate(
            best_class="NO TRADE", confidence=0.80, margin=0.40,
            edge_validated=True, minimum_confidence=0.70,
        )
        self.assertEqual(result["signal"], "NO TRADE")
        self.assertEqual(result["signal_gate"], "model_predicted_no_trade")

    def test_low_confidence_and_low_margin_are_distinguished(self):
        low_confidence = evaluate_signal_gate(
            best_class="LONG", confidence=0.69, margin=0.20,
            edge_validated=True, minimum_confidence=0.70,
        )
        low_margin = evaluate_signal_gate(
            best_class="SHORT", confidence=0.80, margin=0.09,
            edge_validated=True, minimum_confidence=0.70,
        )
        self.assertEqual(low_confidence["signal_gate"], "confidence_below_validated_threshold")
        self.assertEqual(low_margin["signal_gate"], "probability_margin_below_minimum")

    def test_non_finite_or_invalid_thresholds_fail_closed(self):
        for confidence, margin, threshold in (
            (float("nan"), 0.2, 0.7),
            (0.8, float("inf"), 0.7),
            (0.8, 0.2, float("nan")),
        ):
            with self.subTest(confidence=confidence, margin=margin, threshold=threshold):
                result = evaluate_signal_gate(
                    best_class="LONG", confidence=confidence, margin=margin,
                    edge_validated=True, minimum_confidence=threshold,
                )
                self.assertEqual(result["signal"], "NO TRADE")
                self.assertEqual(result["signal_gate"], "invalid_signal_metrics")

    def test_valid_research_candidate_is_labeled_but_not_production_approved(self):
        result = evaluate_signal_gate(
            best_class="SHORT", confidence=0.82, margin=0.21,
            edge_validated=True, minimum_confidence=0.70,
        )
        self.assertEqual(result["signal"], "SHORT")
        self.assertEqual(result["candidate_signal"], "SHORT")
        self.assertEqual(result["signal_gate"], "validated_research_candidate")
        self.assertFalse(result["production_ready"])


if __name__ == "__main__":
    unittest.main()
