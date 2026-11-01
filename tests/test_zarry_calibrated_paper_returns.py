import unittest

import numpy as np
import torch
from torch import nn

from train_kitty_v3_retrained import evaluate_paper_returns


class ConstantLogits(nn.Module):
    def forward(self, values):
        logits = torch.tensor([4.0, 1.0, 0.0], dtype=values.dtype, device=values.device)
        return logits.repeat(values.shape[0], 1)


class CalibratedPaperReturnTests(unittest.TestCase):
    def test_temperature_is_applied_during_paper_return_evaluation(self):
        x = np.zeros((10, 2), dtype=np.float32)
        returns = np.full(10, 0.001, dtype=np.float32)
        result = evaluate_paper_returns(
            ConstantLogits(), x, returns,
            min_confidence=0.50, min_margin=0.0,
            label_threshold=0.001, temperature=2.0,
        )
        self.assertGreater(result["trade_count"], 0)

    def test_non_positive_temperature_is_rejected(self):
        with self.assertRaisesRegex(ValueError, "temperature"):
            evaluate_paper_returns(
                ConstantLogits(), np.zeros((1, 2), dtype=np.float32),
                np.zeros(1, dtype=np.float32), temperature=0.0,
            )


if __name__ == "__main__":
    unittest.main()
