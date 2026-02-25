from dataclasses import dataclass
from typing import List, Dict, Any


@dataclass
class CandidateSelection:
    core_ids: list[str]
    watchlist_ids: list[str]
    borderline_ids: list[str]


# Module constants for thresholds (Issue #5)
DEFAULT_CORE_THRESHOLD = 70
DEFAULT_CORE_CONFIDENCE_THRESHOLD = 0.7
DEFAULT_WATCHLIST_THRESHOLD = 10
DEFAULT_WATCHLIST_CONFIDENCE_THRESHOLD = 0.5

REQUIRED_FIELDS = {"id", "market_score", "trend_delta", "confidence"}


def select_candidates(
    items: List[Dict[str, Any]],
    target_total: int,
    watchlist_ratio: float,
    borderline_band: float,
) -> CandidateSelection:
    """
    Partition items into Core, Watchlist, and Borderline buckets.

    - Core: High market_score + high confidence (stable, mature tech)
    - Watchlist: High trend_delta but lower market_score (emerging/growing tech)
    - Borderline: Items near thresholds or with contradictory signals

    Args:
        items: List of item dicts with id, market_score, trend_delta, confidence
        target_total: Maximum total number of items to select across all buckets
        watchlist_ratio: Ratio of target_total to allocate to watchlist (e.g., 0.3 = 30%)
        borderline_band: Score band around threshold for borderline classification

    Returns:
        CandidateSelection with core_ids, watchlist_ids, borderline_ids

    Raises:
        ValueError: If any item is missing required fields
    """
    # Validate required fields (Issue #2)
    for item in items:
        missing = REQUIRED_FIELDS - set(item.keys())
        if missing:
            raise ValueError(f"Item {item.get('id', '<unknown>')} missing required fields: {missing}")

    # Calculate dynamic thresholds based on borderline_band
    core_threshold = DEFAULT_CORE_THRESHOLD
    core_confidence_threshold = DEFAULT_CORE_CONFIDENCE_THRESHOLD
    watchlist_threshold = DEFAULT_WATCHLIST_THRESHOLD
    watchlist_confidence_threshold = DEFAULT_WATCHLIST_CONFIDENCE_THRESHOLD

    core_candidates = []
    watchlist_candidates = []
    borderline_candidates = []

    for item in items:
        item_id = item["id"]
        market_score = item["market_score"]
        trend_delta = item["trend_delta"]
        confidence = item["confidence"]

        # Core criteria: high market score + high confidence
        is_core = market_score >= core_threshold and confidence >= core_confidence_threshold

        # Watchlist criteria: high trend delta (momentum) + moderate confidence
        is_watchlist = (
            trend_delta >= watchlist_threshold
            and confidence >= watchlist_confidence_threshold
            and not is_core
        )

        # Borderline: items near thresholds or with contradictory signals (Issue #1)
        # Proximity check: items within borderline_band of thresholds
        is_near_core_threshold = abs(market_score - core_threshold) <= borderline_band
        is_near_watchlist_threshold = abs(trend_delta - watchlist_threshold) <= borderline_band
        is_near_confidence_threshold = abs(confidence - core_confidence_threshold) <= (borderline_band / 100)

        is_borderline = (
            confidence < watchlist_confidence_threshold
            or (not is_core and not is_watchlist)
            or (is_near_core_threshold and confidence >= core_confidence_threshold)
            or (is_near_watchlist_threshold and confidence >= watchlist_confidence_threshold)
            or is_near_confidence_threshold
        )

        if is_core:
            core_candidates.append((item_id, market_score, trend_delta))
        elif is_watchlist:
            watchlist_candidates.append((item_id, market_score, trend_delta))
        elif is_borderline:
            borderline_candidates.append((item_id, market_score, trend_delta))

    # Calculate sizes based on ratios and target_total
    watchlist_size = int(target_total * watchlist_ratio)
    remaining = target_total - watchlist_size
    borderline_size = int(remaining * 0.3)  # 30% of remaining for borderline
    core_size = remaining - borderline_size  # Rest for core

    # Sort by relevance per bucket and apply initial size limits
    core_candidates.sort(key=lambda x: x[1], reverse=True)
    watchlist_candidates.sort(key=lambda x: (x[2], x[1]), reverse=True)
    borderline_candidates.sort(key=lambda x: x[1], reverse=True)

    # Stabilize core set: if strict confidence rules produce too few core items,
    # promote top borderline candidates by market score into core.
    if len(items) >= target_total and len(core_candidates) == 0 and borderline_candidates:
        needed = min(core_size, max(1, core_size // 2), len(borderline_candidates))
        promoted = borderline_candidates[:needed]
        core_candidates.extend(promoted)
        borderline_candidates = borderline_candidates[needed:]
        core_candidates.sort(key=lambda x: x[1], reverse=True)

    core_ids = [item_id for item_id, _, _ in core_candidates[:core_size]]
    watchlist_ids = [item_id for item_id, _, _ in watchlist_candidates[:watchlist_size]]
    borderline_ids = [item_id for item_id, _, _ in borderline_candidates[:borderline_size]]

    # Backfill to target_total when any bucket is smaller than expected.
    selected_ids = set(core_ids + watchlist_ids + borderline_ids)
    if len(selected_ids) < target_total:
        remainder = []
        remainder.extend(core_candidates[core_size:])
        remainder.extend(watchlist_candidates[watchlist_size:])
        remainder.extend(borderline_candidates[borderline_size:])
        remainder.sort(key=lambda x: (x[2], x[1]), reverse=True)

        for item_id, _, _ in remainder:
            if len(selected_ids) >= target_total:
                break
            if item_id in selected_ids:
                continue
            borderline_ids.append(item_id)
            selected_ids.add(item_id)

    return CandidateSelection(
        core_ids=core_ids,
        watchlist_ids=watchlist_ids,
        borderline_ids=borderline_ids,
    )
