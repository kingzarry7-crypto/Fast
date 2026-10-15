import tempfile
import unittest
from pathlib import Path

import numpy as np
import pandas as pd
import torch

import train_kitty_v3_retrained as kitty


class KittyTrainingExperimentTests(unittest.TestCase):
    def test_dataset_loader_orders_timestamps_and_accepts_named_labels(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "data.csv"
            rows = []
            for i in range(120):
                row = {feature: float(i + j) for j, feature in enumerate(kitty.FEATURES)}
                row["timestamp"] = pd.Timestamp("2024-01-01", tz="UTC") + pd.Timedelta(hours=119 - i)
                row["target"] = ("SHORT", "NO TRADE", "LONG")[i % 3]
                rows.append(row)
            pd.DataFrame(rows).to_csv(path, index=False)
            x, y, digest = kitty.load_dataset(path)
            self.assertEqual(x.shape, (120, 18))
            self.assertEqual(set(y.tolist()), {0, 1, 2})
            self.assertEqual(len(digest), 64)
            self.assertLess(x[0, 0], x[-1, 0])

    def test_split_is_chronological_and_has_three_partitions(self):
        x = np.arange(120 * 18, dtype=np.float32).reshape(120, 18)
        y = np.arange(120, dtype=np.int64) % 3
        train, validation, test = kitty.split_chronologically(x, y)
        self.assertEqual([len(train[0]), len(validation[0]), len(test[0])], [84, 18, 18])
        self.assertLess(train[0][-1, 0], validation[0][0, 0])
        self.assertLess(validation[0][-1, 0], test[0][0, 0])

    def test_architecture_variants_return_three_class_logits(self):
        for variant in ("baseline", "batchnorm", "leaky_relu"):
            model = kitty.KittyExperimentNet(variant=variant)
            model.eval()
            with torch.inference_mode():
                output = model(torch.zeros(4, 18))
            self.assertEqual(tuple(output.shape), (4, 3))


if __name__ == "__main__":
    unittest.main()
