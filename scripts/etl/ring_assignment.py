"""Deterministic ring assignment with hysteresis and distribution guardrails."""

from __future__ import annotations

from typing import Any, Dict, List, Mapping, Optional


RING_ORDER = ["hold", "assess", "trial", "adopt"]
RING_INDEX = {ring: index for index, ring in enumerate(RING_ORDER)}

DEFAULT_THRESHOLDS = {
    "adopt": 75.0,
    "trial": 55.0,
    "assess": 35.0,
}

DEFAULT_HYSTERESIS = {
    "promote_delta": 5.0,
    "demote_delta": 5.0,
    "cooldown_weeks": 1,
}

DEFAULT_GUARDRAIL = {
    "enabled": True,
    "max_ring_ratio": 0.6,
}


def _clamp(value: float, low: float, high: float) -> float:
    return max(low, min(high, value))


def _get_threshold(target_ring: str, thresholds: Mapping[str, float]) -> float:
    if target_ring == "adopt":
        return float(thresholds.get("adopt", DEFAULT_THRESHOLDS["adopt"]))
    if target_ring == "trial":
        return float(thresholds.get("trial", DEFAULT_THRESHOLDS["trial"]))
    if target_ring == "assess":
        return float(thresholds.get("assess", DEFAULT_THRESHOLDS["assess"]))
    return 0.0


def _ring_from_score(score: float, thresholds: Mapping[str, float]) -> str:
    if score >= _get_threshold("adopt", thresholds):
        return "adopt"
    if score >= _get_threshold("trial", thresholds):
        return "trial"
    if score >= _get_threshold("assess", thresholds):
        return "assess"
    return "hold"


def _apply_hysteresis(
    score: float,
    proposed_ring: str,
    previous_ring: str,
    thresholds: Mapping[str, float],
    hysteresis: Mapping[str, float],
) -> str:
    previous_index = RING_INDEX.get(previous_ring)
    proposed_index = RING_INDEX.get(proposed_ring)
    if previous_index is None or proposed_index is None or proposed_index == previous_index:
        return proposed_ring

    promote_delta = float(hysteresis.get("promote_delta", DEFAULT_HYSTERESIS["promote_delta"]))
    demote_delta = float(hysteresis.get("demote_delta", DEFAULT_HYSTERESIS["demote_delta"]))

    if proposed_index > previous_index:
        required_score = _get_threshold(proposed_ring, thresholds) + promote_delta
        if score < required_score:
            return previous_ring

    if proposed_index < previous_index:
        required_score = _get_threshold(previous_ring, thresholds) - demote_delta
        if score > required_score:
            return previous_ring

    return proposed_ring


def _rebalance_if_needed(items: List[Dict[str, Any]], max_ring_ratio: float) -> None:
    if not items:
        return

    max_count = int(len(items) * max_ring_ratio)
    if max_count <= 0:
        max_count = 1

    def ring_count(ring: str) -> int:
        return sum(1 for item in items if item.get("ring") == ring)

    for dominant_ring in ["adopt", "trial", "assess", "hold"]:
        while ring_count(dominant_ring) > max_count:
            dominant_items = [item for item in items if item.get("ring") == dominant_ring]
            if not dominant_items:
                break

            dominant_items.sort(key=lambda item: float(item.get("market_score", 0.0)))
            candidate = dominant_items[0]
            ring_index = RING_INDEX[dominant_ring]
            if ring_index > 0:
                candidate["ring"] = RING_ORDER[ring_index - 1]
            elif ring_index < len(RING_ORDER) - 1:
                candidate["ring"] = RING_ORDER[ring_index + 1]
            else:
                break


def assign_rings(
    items: List[Dict[str, Any]],
    previous: Optional[Mapping[str, Any]] = None,
    thresholds: Optional[Mapping[str, float]] = None,
    hysteresis: Optional[Mapping[str, float]] = None,
    guardrail: Optional[Mapping[str, Any]] = None,
) -> List[Dict[str, Any]]:
    thresholds = thresholds or DEFAULT_THRESHOLDS
    hysteresis = hysteresis or DEFAULT_HYSTERESIS
    guardrail = guardrail or DEFAULT_GUARDRAIL
    previous = previous or {}

    assigned: List[Dict[str, Any]] = []
    for item in items:
        item_copy = dict(item)
        item_id = str(item_copy.get("id", ""))
        score = float(item_copy.get("market_score", 0.0)) + float(item_copy.get("trend_delta", 0.0))
        score = _clamp(score, 0.0, 100.0)

        proposed = _ring_from_score(score, thresholds)
        previous_entry = previous.get(item_id)
        previous_ring = previous_entry.get("ring") if isinstance(previous_entry, dict) else previous_entry
        if isinstance(previous_ring, str) and previous_ring in RING_INDEX:
            proposed = _apply_hysteresis(score, proposed, previous_ring, thresholds, hysteresis)

        item_copy["ring"] = proposed
        item_copy["previous_ring"] = previous_ring
        assigned.append(item_copy)

    if bool(guardrail.get("enabled", True)):
        max_ratio = float(guardrail.get("max_ring_ratio", DEFAULT_GUARDRAIL["max_ring_ratio"]))
        _rebalance_if_needed(assigned, _clamp(max_ratio, 0.05, 1.0))

    return assigned
