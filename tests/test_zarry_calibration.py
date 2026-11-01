import unittest
import numpy as np

from zarry_calibration import fit_temperature_from_logits, probabilities_from_logits, labels_from_forward_returns


class ProbabilityCalibrationTests(unittest.TestCase):
    def test_temperature_reduces_nll_for_overconfident_logits(self):
        labels = np.array([0, 1, 2] * 40)
        logits = np.full((len(labels), 3), -3.0)
        logits[np.arange(len(labels)), labels] = 3.0
        # Flip a controlled portion of predictions to represent imperfect fit.
        logits[:24] = logits[:24][:, ::-1]
        result = fit_temperature_from_logits(logits, labels)
        self.assertGreater(result["temperature"], 1.0)
        self.assertLess(result["after"]["nll"], result["before"]["nll"])

    def test_label_threshold_rebuilds_three_classes_from_forward_returns(self):
        labels = labels_from_forward_returns(np.array([-0.002, -0.0005, 0.001, 0.002]), 0.001)
        self.assertEqual(labels.tolist(), [0, 1, 2, 2])

    def test_probability_temperature_preserves_normalized_rows(self):
        probs = probabilities_from_logits(np.array([[2.0, 1.0, 0.0]]), 2.0)
        self.assertAlmostEqual(float(probs.sum()), 1.0)
        self.assertGreater(probs[0, 0], probs[0, 1])


if __name__ == "__main__":
    unittest.main()
