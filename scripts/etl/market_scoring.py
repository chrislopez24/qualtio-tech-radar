"""Deterministic market scoring for external signals."""

from __future__ import annotations

from typing import Mapping


# Default weights without Google Trends
# GitHub is primary source (real adoption), HN is secondary (early buzz)
DEFAULT_WEIGHTS = {
    "gh_momentum": 0.60,
    "gh_popularity": 0.25,
    "hn_heat": 0.15,
}


def _clamp(value: float, low: float, high: float) -> float:
    return max(low, min(high, value))


def score_technology(signals: Mapping[str, float], weights: Mapping[str, float] | None = None) -> float:
    active_weights = weights or DEFAULT_WEIGHTS
    total = 0.0
    for name, weight in active_weights.items():
        signal_value = float(signals.get(name, 0.0))
        total += _clamp(signal_value, 0.0, 100.0) * float(weight)
    return _clamp(total, 0.0, 100.0)


def calculate_confidence(source_count: int, variance: float) -> float:
    base = 0.35 + (max(0, source_count) * 0.18)
    penalty = _clamp(variance / 1000.0, 0.0, 0.5)
    return _clamp(base - penalty, 0.0, 1.0)
