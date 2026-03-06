"""Deterministic market scoring for external signals."""

from __future__ import annotations

import math
from typing import Mapping


# Default weights for the supported external signals.
# GitHub is primary source (real adoption), HN is secondary (early buzz)
DEFAULT_WEIGHTS = {
    "gh_momentum": 0.60,
    "gh_popularity": 0.25,
    "hn_heat": 0.15,
}


def _clamp(value: float, low: float, high: float) -> float:
    return max(low, min(high, value))


def _infer_source_count(signals: Mapping[str, float]) -> int:
    gh_present = float(signals.get("gh_momentum", 0.0)) > 0.0 or float(signals.get("gh_popularity", 0.0)) > 0.0
    hn_present = float(signals.get("hn_heat", 0.0)) > 0.0
    return int(gh_present) + int(hn_present)


def _log_bonus(value: float, reference: float, max_bonus: float) -> float:
    if value <= 0.0 or reference <= 0.0:
        return 0.0
    scaled = math.log10(1.0 + value) / math.log10(1.0 + reference)
    return _clamp(scaled * max_bonus, 0.0, max_bonus)


def score_technology(
    signals: Mapping[str, float],
    weights: Mapping[str, float] | None = None,
    *,
    source_count: int | None = None,
    github_stars: float = 0.0,
    github_forks: float = 0.0,
) -> float:
    active_weights = weights or DEFAULT_WEIGHTS

    gh_momentum = _clamp(float(signals.get("gh_momentum", 0.0)), 0.0, 100.0)
    gh_popularity = _clamp(float(signals.get("gh_popularity", 0.0)), 0.0, 100.0)
    hn_heat = _clamp(float(signals.get("hn_heat", 0.0)), 0.0, 100.0)

    total = 0.0
    for name, weight in active_weights.items():
        signal_value = {
            "gh_momentum": gh_momentum,
            "gh_popularity": gh_popularity,
            "hn_heat": hn_heat,
        }.get(name, _clamp(float(signals.get(name, 0.0)), 0.0, 100.0))
        total += _clamp(signal_value, 0.0, 100.0) * float(weight)

    effective_source_count = max(0, source_count if source_count is not None else _infer_source_count(signals))
    github_present = gh_momentum > 0.0 or gh_popularity > 0.0
    hn_present = hn_heat > 0.0

    source_diversity_bonus = 0.0
    if effective_source_count > 1 and github_present and hn_present:
        source_diversity_bonus = 2.5 + min(1.5, hn_heat / 40.0)

    github_strength_bonus = 0.0
    if github_present and (github_stars > 0.0 or github_forks > 0.0):
        github_strength_bonus = _log_bonus(github_stars, 250000.0, 4.0) + _log_bonus(github_forks, 50000.0, 3.0)
        if not hn_present:
            github_strength_bonus *= 0.75

    low_signal_penalty = 0.0
    total_signal = gh_momentum + gh_popularity + hn_heat
    if effective_source_count <= 1:
        if github_present and not hn_present:
            if gh_momentum >= 95.0 and gh_popularity >= 95.0:
                low_signal_penalty += 6.0
            elif total_signal < 120.0:
                low_signal_penalty += 2.0
        elif hn_present and not github_present:
            low_signal_penalty += 4.0 + max(0.0, (60.0 - min(hn_heat, 60.0)) / 15.0)

    adjusted = total + source_diversity_bonus + github_strength_bonus - low_signal_penalty
    return _clamp(adjusted, 0.0, 100.0)


def calculate_confidence(source_count: int, variance: float) -> float:
    base = 0.35 + (max(0, source_count) * 0.18)
    penalty = _clamp(variance / 1000.0, 0.0, 0.5)
    return _clamp(base - penalty, 0.0, 1.0)
