"""Audit exported Kitty V3 target timestamps before enabling inference.

Expected CSV columns: split, signal_time, entry_time, exit_time.
Optional columns: target, signal_segment, entry_segment, exit_segment.
The audit fails closed when a label's exit reaches or crosses the next split's
first signal timestamp. Run against the exact rows used for training, not a
reconstructed summary. This utility never enables prediction or trading.
"""
from __future__ import annotations

import argparse
from pathlib import Path

import pandas as pd

SPLIT_ORDER = ("train", "validation", "test")
REQUIRED = ("split", "signal_time", "entry_time", "exit_time")


def audit_frame(frame: pd.DataFrame) -> list[str]:
    errors: list[str] = []
    missing = [name for name in REQUIRED if name not in frame.columns]
    if missing:
        return ["missing required columns: " + ", ".join(missing)]
    if frame.empty:
        return ["CSV contains no rows"]

    data = frame.copy()
    unknown = sorted(set(data["split"].dropna().astype(str)) - set(SPLIT_ORDER))
    if unknown:
        errors.append("unknown split names: " + ", ".join(unknown))
    if data["split"].isna().any():
        errors.append("split contains null values")

    for column in ("signal_time", "entry_time", "exit_time"):
        data[column] = pd.to_datetime(data[column], utc=True, errors="coerce")
        if data[column].isna().any():
            errors.append(f"{column} contains invalid or missing timestamps")

    if not any(data[c].isna().any() for c in ("signal_time", "entry_time", "exit_time")):
        if not (data["entry_time"] > data["signal_time"]).all():
            errors.append("every entry_time must be strictly after signal_time")
        if not (data["exit_time"] > data["entry_time"]).all():
            errors.append("every exit_time must be strictly after entry_time")
        if data["signal_time"].duplicated().any():
            errors.append("signal_time contains duplicates; verify row identity")

        first_by_split: dict[str, pd.Timestamp] = {}
        for split in SPLIT_ORDER:
            subset = data.loc[data["split"].astype(str) == split, "signal_time"]
            if not subset.empty:
                first_by_split[split] = subset.min()

        present = [name for name in SPLIT_ORDER if name in first_by_split]
        for previous, following in zip(present, present[1:]):
            boundary = first_by_split[following]
            previous_rows = data[data["split"].astype(str) == previous]
            leaks = previous_rows[previous_rows["exit_time"] >= boundary]
            if not leaks.empty:
                errors.append(
                    f"{previous} has {len(leaks)} label(s) whose exit_time reaches/crosses "
                    f"{following} start {boundary.isoformat()}; purge these rows"
                )

    if "target" in data.columns:
        targets = pd.to_numeric(data["target"], errors="coerce")
        if targets.isna().any() or not targets.isin([0, 1, 2]).all():
            errors.append("target must contain only class IDs 0, 1, 2")

    for left, right in (("signal_segment", "entry_segment"), ("signal_segment", "exit_segment")):
        if left in data.columns and right in data.columns:
            if (data[left].astype(str) != data[right].astype(str)).any():
                errors.append(f"{left} and {right} differ; target window crosses a data segment")

    return errors


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("csv", type=Path, help="Exported labeled rows with split and target timestamps")
    args = parser.parse_args()
    try:
        frame = pd.read_csv(args.csv)
    except Exception as exc:
        print(f"FAIL: could not read {args.csv}: {type(exc).__name__}: {exc}")
        return 2

    errors = audit_frame(frame)
    if errors:
        print("KITTY V3 SPLIT AUDIT FAILED")
        for error in errors:
            print("- " + error)
        return 1
    print("KITTY V3 SPLIT AUDIT PASSED")
    print(f"Rows audited: {len(frame)}")
    print("Prediction remains paper-only; this report does not establish profitability.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
