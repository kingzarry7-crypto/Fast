import unittest

import pandas as pd

from scripts.audit_kitty_v3_split_boundaries import audit_frame


class KittyV3SplitAuditTests(unittest.TestCase):
    def base_rows(self):
        return pd.DataFrame([
            {"split": "train", "signal_time": "2026-01-01T00:00:00Z", "entry_time": "2026-01-01T01:00:00Z", "exit_time": "2026-01-01T06:00:00Z", "target": 0},
            {"split": "validation", "signal_time": "2026-01-01T07:00:00Z", "entry_time": "2026-01-01T08:00:00Z", "exit_time": "2026-01-01T13:00:00Z", "target": 1},
            {"split": "test", "signal_time": "2026-01-01T14:00:00Z", "entry_time": "2026-01-01T15:00:00Z", "exit_time": "2026-01-01T20:00:00Z", "target": 2},
        ])

    def test_passes_when_prior_split_exits_before_next_split(self):
        self.assertEqual(audit_frame(self.base_rows()), [])

    def test_fails_when_train_label_exit_equals_validation_start(self):
        frame = self.base_rows()
        frame.loc[0, "exit_time"] = "2026-01-01T07:00:00Z"
        errors = audit_frame(frame)
        self.assertTrue(any("train has 1 label(s)" in error for error in errors), errors)

    def test_fails_when_target_window_crosses_segment(self):
        frame = self.base_rows()
        frame["signal_segment"] = [0, 1, 2]
        frame["entry_segment"] = [0, 1, 2]
        frame["exit_segment"] = [1, 1, 2]
        errors = audit_frame(frame)
        self.assertTrue(any("target window crosses a data segment" in error for error in errors), errors)

    def test_fails_invalid_class_id(self):
        frame = self.base_rows()
        frame.loc[1, "target"] = 3
        errors = audit_frame(frame)
        self.assertTrue(any("class IDs" in error for error in errors), errors)


if __name__ == "__main__":
    unittest.main()
