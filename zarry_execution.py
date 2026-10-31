"""Shared execution simulator for all research-only ZARRY strategy evaluations.

Decision at row t enters at the next open and exits at t+7 close for the
six-hour holding horizon. A decision on the previous exit candle is eligible.
Returns are forward-price proxies, not realized broker fills.
"""
from __future__ import annotations

import math
from typing import Sequence


def simulate_non_overlapping_trades(
    forward_returns: Sequence[float],
    directions: Sequence[int],
    *,
    round_trip_cost: float,
    outcome_horizon_rows: int = 7,
) -> dict:
    """Apply one frozen execution convention to model and rule predictions.

    directions use -1 for SHORT, 0 for NO TRADE, and +1 for LONG.
    """
    if len(forward_returns) != len(directions):
        raise ValueError("forward_returns and directions must have equal lengths")
    if outcome_horizon_rows < 1:
        raise ValueError("outcome_horizon_rows must be positive")
    cost = float(round_trip_cost)
    if not math.isfinite(cost) or cost < 0:
        raise ValueError("round_trip_cost must be finite and non-negative")

    net_returns: list[float] = []
    trade_indices: list[dict[str, int]] = []
    overlap_skips = 0
    incomplete_skips = 0
    next_entry_index = 0

    for index, (raw_return, raw_direction) in enumerate(zip(forward_returns, directions)):
        direction = int(raw_direction)
        if direction not in (-1, 0, 1):
            raise ValueError("directions must contain only -1, 0, or +1")
        if direction == 0:
            continue
        if index < next_entry_index:
            overlap_skips += 1
            continue
        exit_index = index + outcome_horizon_rows
        if exit_index >= len(forward_returns):
            incomplete_skips += 1
            continue
        value = float(raw_return)
        if not math.isfinite(value):
            raise ValueError("forward returns must be finite for every eligible trade")
        net_returns.append(direction * value - cost)
        trade_indices.append({"entry_index": index, "exit_index": exit_index})
        # t+7 is the exit candle and is itself the next eligible decision candle.
        next_entry_index = exit_index

    equity = 1.0
    peak = 1.0
    max_drawdown = 0.0
    gross_profit = 0.0
    gross_loss = 0.0
    wins = 0
    for result in net_returns:
        equity *= 1.0 + result
        peak = max(peak, equity)
        max_drawdown = min(max_drawdown, equity / peak - 1.0)
        if result > 0:
            wins += 1
            gross_profit += result
        elif result < 0:
            gross_loss += -result

    count = len(net_returns)
    profit_factor = (
        gross_profit / gross_loss if gross_loss > 0
        else (999.0 if gross_profit > 0 else (None if count == 0 else 0.0))
    )
    return {
        "trade_count": count,
        "win_rate": wins / count if count else None,
        "average_net_return": sum(net_returns) / count if count else None,
        "profit_factor": profit_factor,
        "compounded_net_return": equity - 1.0,
        "max_drawdown": max_drawdown,
        "skipped_overlapping_signals": overlap_skips,
        "skipped_incomplete_outcomes": incomplete_skips,
        "net_trade_returns": net_returns,
        "trade_indices": trade_indices,
        "exposure_fraction": (count * (outcome_horizon_rows - 1) / len(forward_returns)) if forward_returns else 0.0,
        "round_trip_cost_assumption": cost,
        "outcome_type": "forward_price_proxy_not_realized_paper_trade",
    }
