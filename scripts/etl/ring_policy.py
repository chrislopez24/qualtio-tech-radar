from __future__ import annotations

from typing import Mapping


RING_ORDER = ("hold", "assess", "trial", "adopt")
RING_INDEX = {ring: index for index, ring in enumerate(RING_ORDER)}

DEFAULT_THRESHOLDS = {
    "adopt": 80.0,
    "trial": 60.0,
    "assess": 40.0,
}

DEFAULT_HYSTERESIS = {
    "promote_delta": 15.0,
    "demote_delta": 15.0,
}


def _threshold_for(ring: str, thresholds: Mapping[str, float]) -> float:
    if ring == "adopt":
        return float(thresholds.get("adopt", DEFAULT_THRESHOLDS["adopt"]))
    if ring == "trial":
        return float(thresholds.get("trial", DEFAULT_THRESHOLDS["trial"]))
    if ring == "assess":
        return float(thresholds.get("assess", DEFAULT_THRESHOLDS["assess"]))
    return 0.0


def _ring_from_composite(composite: float, thresholds: Mapping[str, float]) -> str:
    if composite >= _threshold_for("adopt", thresholds):
        return "adopt"
    if composite >= _threshold_for("trial", thresholds):
        return "trial"
    if composite >= _threshold_for("assess", thresholds):
        return "assess"
    return "hold"


def _cap_ring(candidate: str, maximum_ring: str) -> str:
    candidate_index = RING_INDEX[candidate]
    maximum_index = RING_INDEX[maximum_ring]
    return RING_ORDER[min(candidate_index, maximum_index)]


def _apply_hysteresis(
    composite: float,
    proposed_ring: str,
    previous_ring: str | None,
    thresholds: Mapping[str, float],
    hysteresis: Mapping[str, float],
    ceiling_ring: str,
) -> str:
    if previous_ring not in RING_INDEX or proposed_ring not in RING_INDEX:
        return proposed_ring

    previous_index = RING_INDEX[previous_ring]
    proposed_index = RING_INDEX[proposed_ring]
    if previous_index == proposed_index:
        return proposed_ring

    promote_delta = float(hysteresis.get("promote_delta", DEFAULT_HYSTERESIS["promote_delta"]))
    demote_delta = float(hysteresis.get("demote_delta", DEFAULT_HYSTERESIS["demote_delta"]))

    if proposed_index > previous_index:
        for candidate_index in range(proposed_index, previous_index, -1):
            candidate_ring = RING_ORDER[candidate_index]
            required_score = _threshold_for(candidate_ring, thresholds) + promote_delta
            if composite >= required_score:
                return _cap_ring(candidate_ring, ceiling_ring)
        return _cap_ring(previous_ring, ceiling_ring)

    if proposed_index < previous_index:
        required_score = _threshold_for(previous_ring, thresholds) - demote_delta
        if composite > required_score:
            return _cap_ring(previous_ring, ceiling_ring)

    return proposed_ring


def decide_ring(
    scores: Mapping[str, float],
    *,
    source_coverage: int,
    has_external_adoption: bool = False,
    github_only: bool = False,
    editorial_exception: bool = False,
    previous_ring: str | None = None,
    thresholds: Mapping[str, float] | None = None,
    hysteresis: Mapping[str, float] | None = None,
) -> str:
    active_thresholds = thresholds or DEFAULT_THRESHOLDS
    active_hysteresis = hysteresis or DEFAULT_HYSTERESIS
    composite = float(scores.get("composite", 0.0) or 0.0)

    proposed = _ring_from_composite(composite, active_thresholds)

    ceiling_ring = "adopt"
    if not has_external_adoption or github_only:
        ceiling_ring = "trial"

    trial_allowed = (
        has_external_adoption
        or (source_coverage >= 2 and not github_only)
        or editorial_exception
    )
    if not trial_allowed:
        ceiling_ring = "assess"

    proposed = _cap_ring(proposed, ceiling_ring)
    return _apply_hysteresis(
        composite,
        proposed,
        previous_ring,
        active_thresholds,
        active_hysteresis,
        ceiling_ring,
    )
